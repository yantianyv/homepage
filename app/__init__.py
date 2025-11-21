import os
from flask import Flask
from app.config import UPLOAD_PATH

def create_app():
    app = Flask(__name__, 
                static_folder="../static", 
                template_folder="../templates")
    app.secret_key = os.urandom(24)
    app.config["UPLOAD_FOLDER"] = UPLOAD_PATH
    
    from app.routes import bp
    app.register_blueprint(bp)
    
    return app
