import os
import sys
from flask import Flask

def get_base_dir():
    """
    Determine the base directory of the application.
    Elegant solution: Check the entry point extension.
    - If running a .py script, we are in development (use script dir).
    - If running an executable (no extension or .exe), we are in production (use exe dir).
    """
    # Get the absolute path of the entry point (run.py or the exe)
    entry_point = os.path.abspath(sys.argv[0])
    
    if entry_point.endswith('.py'):
        # Development mode: base dir is where run.py is
        return os.path.dirname(entry_point)
    
    # Compiled mode: base dir is where the executable is
    return os.path.dirname(sys.executable)

BASE_DIR = get_base_dir()
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

def create_app():
    # In Nuitka --onefile, resources included with --include-data-dir=templates=templates 
    # are placed in the root of the temp directory, alongside run.py (or the executable logic).
    # app/__init__.py is in app/ subdirectory.
    # So we need to go up one level from __file__ to find 'templates' and 'static'.
    
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    template_dir = os.path.join(root_dir, 'templates')
    static_dir = os.path.join(root_dir, 'static')

    app = Flask(__name__,
                static_folder=static_dir,
                template_folder=template_dir)
    app.secret_key = os.urandom(24)

    from app.routes import bp
    app.register_blueprint(bp)

    return app
