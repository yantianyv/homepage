import os
import sys
from flask import Flask
from app.config import UPLOAD_PATH

def create_app():
    # Calculate base directory - works for both development and compiled environments
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        base_dir = os.path.dirname(sys.executable)
    else:
        # Running as Python script
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    template_dir = os.path.join(base_dir, 'templates')
    static_dir = os.path.join(base_dir, 'static')

    app = Flask(__name__,
                static_folder=static_dir,
                template_folder=template_dir)
    app.secret_key = os.urandom(24)
    app.config["UPLOAD_FOLDER"] = UPLOAD_PATH
    
    from app.routes import bp
    app.register_blueprint(bp)
    
    return app
