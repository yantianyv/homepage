import time
import threading
from scripts import get_favicon
from app.config import config

def refresh_favicon_and_config():
    while True:
        try:
            get_favicon.refresh()
        except Exception as e:
            print(f"Error refreshing favicons: {e}")
        
        for _ in range(60):
            try:
                config.load()
            except Exception as e:
                print(f"Error reloading config: {e}")
            time.sleep(1)

def start_background_tasks():
    refresh_thread = threading.Thread(
        target=refresh_favicon_and_config, 
        daemon=True
    )
    refresh_thread.start()
