import os
import sys
import time

from src.config import SRC_DIR, ERROR_COLOR
from src.utils.helpers import console, clear_header, show_menu, run_script

SUB_TITLE = """  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
  ┃   Casino Promocode Claimer   ┃
  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n"""

def main():
    title = "Ave X Launcher - Casino Promocode Claimer"
    os.system(f"title {title}")

    bypass_env = os.environ.get("PROMOCODE_BYPASS")
    site_env = os.environ.get("PROMOCODE_SITE")

    bypass_choice = bypass_env if bypass_env else "none"
    website_choice = site_env if site_env else "MM2WILD"

    bypass_label = "Camoufox CF Bypasser" if bypass_choice == "camoufox_solver" else "Sin Bypasser"

    title += f" - [{bypass_label}] - [{website_choice}]"
    os.system(f"title {title}")
    clear_header(SUB_TITLE)

    script_path = os.path.join(SRC_DIR, "modules", "casino_promocode_claimer.py")
    if os.path.exists(script_path):
        run_script(script_path, bypass_choice, website_choice)
    else:
        console.print(f"[ERROR] No se encontró: {script_path}", style=ERROR_COLOR)
        time.sleep(2)

if __name__ == "__main__":
    main()
