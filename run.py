import sys
import os
import json
from app import create_app, CONFIG_FILE
from app.services import start_background_tasks
from scripts import set_cfg

PORT = 80

if len(sys.argv) > 1:
    if sys.argv[1] == "--help" or sys.argv[1] == "-h":
        help_text = f"""
        Usage: python run.py [options]
        Options:
        -h, --help            Show this help message
        -s, --set            Set configuration
        -p, --port PORT       Run with specified port (default: {PORT})
        --shutdown            Shutdown server
        """
        print(help_text)
        sys.exit(0)
    
    elif sys.argv[1] == "--set" or sys.argv[1] == "-s":
        set_cfg.main_menu()
        sys.exit(0)
    
    elif sys.argv[1] == "--port" or sys.argv[1] == "-p":
        if len(sys.argv) > 2:
            PORT = int(sys.argv[2])
        else:
            print("Error: Port number not specified. Using default port 80.")
    
    elif sys.argv[1] == "--shutdown":
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config_data = json.load(f)
            config_data["shutdown"] = True
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config_data, f, ensure_ascii=False, indent=4)
            print("Server will shut down shortly.")
        except Exception as e:
            print(f"Error initiating shutdown: {e}")
        sys.exit(0)
    
    else:
        print(f"Unknown option: {sys.argv[1]}")
        sys.exit(1)

if __name__ == "__main__":
    # Reset shutdown flag
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config_data = json.load(f)
        if config_data.get("shutdown"):
            config_data["shutdown"] = False
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config_data, f, ensure_ascii=False, indent=4)
    except:
        pass

    app = create_app()
    start_background_tasks()
    
    try:
        app.run(host="0.0.0.0", port=PORT)
    except Exception as e:
        print(f"Flask failed to start: {e}")
        os._exit(1)
