import os
from datetime import datetime
from flask import Blueprint, render_template, redirect, request, send_from_directory, current_app
from app.config import config, FILES_PATH
from app import BASE_DIR
from app.utils import get_downloadable_files

bp = Blueprint('main', __name__)

@bp.context_processor
def inject_now():
    return {"now": datetime.now}

@bp.route("/")
def index():
    services_with_domains = {}
    services = config.get("services", {})
    default_domain = config.default_domain

    for service_id, service_info in services.items():
        service_with_domain = service_info.copy()
        service_with_domain["domain"] = service_info.get("domain", default_domain)
        services_with_domains[service_id] = service_with_domain

    return render_template("index.html",
                         services=services_with_domains,
                         downloads=get_downloadable_files(),
                         site_title=config.get("site_title", "Service Navigation Center"))

@bp.route("/<service>")
def redirect_to_service(service):
    services = config.get("services", {})
    if service in services:
        service_info = services[service]
        port = service_info["port"]
        domain = service_info.get("domain", config.default_domain)
        return redirect(f"http://{domain}:{port}")
    return "Service not found", 404

@bp.route("/favicon/<service_id>")
def get_service_favicon(service_id):
    try:
        services = config.get("services", {})
        if service_id not in services:
            return "Service not found", 404
        
        favicon_name = services[service_id].get("favicon")
        if not favicon_name:
            return "Favicon not configured", 404
        
        favicon_path = os.path.join(BASE_DIR, "favicons", favicon_name)
        if not os.path.exists(favicon_path):
            return "Favicon file not found", 404
        
        _, ext = os.path.splitext(favicon_name.lower())
        mime_types = {
            '.ico': 'image/x-icon',
            '.svg': 'image/svg+xml',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif'
        }
        mimetype = mime_types.get(ext, 'application/octet-stream')
        
        return send_from_directory(
            directory=os.path.join(BASE_DIR, "favicons"),
            path=favicon_name,
            mimetype=mimetype
        )
    except Exception as e:
        current_app.logger.error(f"Error serving favicon: {e}")
        return "Internal server error", 500

@bp.route("/download/<path:filepath>")
def download_file(filepath):
    try:
        filepath = os.path.normpath(filepath)
        filename = os.path.basename(filepath)
        file_dir = os.path.dirname(filepath)
        full_path = os.path.join(FILES_PATH, filepath)

        if os.path.exists(full_path):
            if file_dir:
                return send_from_directory(os.path.join(FILES_PATH, file_dir), filename,
                                        as_attachment=True, download_name=filename)
            else:
                return send_from_directory(FILES_PATH, filename,
                                      as_attachment=True, download_name=filename)
        else:
            return "File not found", 404
    except Exception as e:
        current_app.logger.error(f"Error downloading file {filepath}: {e}")
        return "Error downloading file", 500
