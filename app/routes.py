import os
import uuid
import json
from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, request, send_from_directory, jsonify, current_app
from werkzeug.utils import secure_filename
from app.config import config, BASE_DIR, UPLOAD_PATH, FILES_PATH, UPLOAD_FOLDER
from app.utils import get_downloadable_files, get_temp_files, get_client_info

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
                         temp_files=get_temp_files(), 
                         site_title=config.get("site_title", "Service Navigation Center"), 
                         show_upload=True)

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

from werkzeug.security import generate_password_hash, check_password_hash

@bp.route("/upload", methods=["GET", "POST"])
def upload_file():
    if request.method == "POST":
        if "file" not in request.files:
            return jsonify({"success": False, "message": "No file selected"}), 400

        file = request.files["file"]
        if file.filename == "":
            return jsonify({"success": False, "message": "No file selected"}), 400

        if file:
            try:
                filename = secure_filename(file.filename)
                unique_filename = f"{uuid.uuid4().hex[:8]}_{filename}"
                filepath = os.path.join(UPLOAD_PATH, unique_filename)
                temp_filepath = filepath + ".part"

                # Use Flask's save method which is optimized (uses shutil.copyfileobj)
                file.save(temp_filepath)
                
                # Atomic move after write is complete
                os.rename(temp_filepath, filepath)

                description = request.form.get("description", "").strip() or "上传者没有提供描述信息"
                password = request.form.get("password", "").strip()
                expiration_hours = int(request.form.get("expiration", 24))
                
                upload_time = datetime.now()
                expiration_time = upload_time + timedelta(hours=expiration_hours)
                
                desc_data = {
                    "description": description, 
                    "uploader": get_client_info(), 
                    "upload_time": upload_time.isoformat(), 
                    "expiration_time": expiration_time.isoformat(),
                    "original_filename": file.filename
                }
                
                if password:
                    desc_data["password_hash"] = generate_password_hash(password)

                with open(os.path.join(UPLOAD_PATH, f".{unique_filename}.json"), "w", encoding="utf-8") as f:
                    json.dump(desc_data, f, ensure_ascii=False, indent=2)

                return jsonify({"success": True, "message": "File uploaded successfully!"})
            except Exception as e:
                current_app.logger.error(f"Error uploading file: {e}")
                if os.path.exists(filepath):
                    os.remove(filepath)
                return jsonify({"success": False, "message": "Upload failed"}), 500
    
    return render_template("upload.html", site_title=config.get("site_title", "Service Navigation Center"))

@bp.route("/download/<path:filepath>", methods=["GET", "POST"])
def download_file(filepath):
    try:
        filepath = os.path.normpath(filepath)
        filename = os.path.basename(filepath)
        file_dir = os.path.dirname(filepath)
        full_path = os.path.join(FILES_PATH, filepath)

        if os.path.exists(full_path):
            desc_file = os.path.join(UPLOAD_PATH, f".{filename}.json")
            original_filename = filepath
            password_hash = None
            
            if os.path.exists(desc_file):
                try:
                    with open(desc_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        original_filename = data.get("original_filename", filename)
                        password_hash = data.get("password_hash")
                except:
                    pass
            
            # Check password protection
            if password_hash:
                if request.method == "POST":
                    password = request.form.get("password", "")
                    if check_password_hash(password_hash, password):
                        # Password correct, proceed to download
                        pass
                    else:
                        return render_template("password.html", 
                                            filename=original_filename, 
                                            error=True,
                                            site_title=config.get("site_title", "Service Navigation Center"))
                else:
                    return render_template("password.html", 
                                        filename=original_filename, 
                                        error=False,
                                        site_title=config.get("site_title", "Service Navigation Center"))

            if file_dir:
                return send_from_directory(os.path.join(FILES_PATH, file_dir), filename, 
                                        as_attachment=True, download_name=original_filename)
            else:
                return send_from_directory(FILES_PATH, filename, 
                                      as_attachment=True, download_name=original_filename)
        else:
            return "File not found", 404
    except Exception as e:
        current_app.logger.error(f"Error downloading file {filepath}: {e}")
        return "Error downloading file", 500
