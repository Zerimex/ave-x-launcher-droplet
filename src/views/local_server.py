import os
import time

from src.config import SRC_DIR, ERROR_COLOR
from src.utils.helpers import console, clear_header, get_user_config, run_script

SUB_TITLE = """  ┏━━━━━━━━━━━━━━━━━━━━━━━┓
  ┃  Solver Socket Server ┃
  ┗━━━━━━━━━━━━━━━━━━━━━━━┛\n"""

def main():
    config = get_user_config()
    host = config.get("socket_host", "127.0.0.1")
    port = config.get("socket_port", 65432)
    server_addr = f"{host}:{port}"
    title = f"Ave X Launcher - Solver Socket Server - [{server_addr}]"
    os.system(f"title {title}")
    try:
        clear_header(SUB_TITLE)
        script_path = os.path.join(SRC_DIR, "modules", "local_server.py")
        if os.path.exists(script_path):
                run_script(script_path)
        else:
            time.sleep(0.8)
            console.print(f"[ERROR] No se encontró: {script_path}", style=ERROR_COLOR)
            time.sleep(2)

    except Exception as e:
        console.print(f"[PYTHON ERROR] {e}", style=ERROR_COLOR)
        time.sleep(3)

if __name__ == "__main__":
    main()
