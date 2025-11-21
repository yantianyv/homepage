import json
import os
import sys
from scripts import set_cfg

# Define paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if "__compiled__" in globals():
    if os.name == "posix":
        BASE_DIR = os.getcwd()
    else:
        BASE_DIR = os.path.dirname(sys.executable)

CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
FILES_PATH = os.path.join(BASE_DIR, "files")
UPLOAD_FOLDER = ".tempfiles"
UPLOAD_PATH = os.path.join(FILES_PATH, UPLOAD_FOLDER)

# Ensure directories exist
os.makedirs(UPLOAD_PATH, exist_ok=True)
os.makedirs(FILES_PATH, exist_ok=True)

class Config:
    def __init__(self):
        self.data = {}
        self.default_domain = "127.0.0.1"
        self.load()

    def load(self):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                self.data = json.load(f)
        except Exception:
            print("Config not found or invalid. Launching setup...")
            set_cfg.main_menu()
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                self.data = json.load(f)

        self.default_domain = self.data.get("default_domain", "127.0.0.1")
        
        if self.data.get("shutdown"):
            print("Service shutdown requested.")
            os._exit(0)

    def save(self):
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=4)

    def get(self, key, default=None):
        return self.data.get(key, default)

config = Config()
