import os
import time

from src.config import SRC_DIR, ERROR_COLOR
from src.utils.helpers import console, clear_header, show_menu, run_script

SUB_TITLE = """  ┏━━━━━━━━━━━━━━━━━━━━━━━━━┓
  ┃   Casino Rain Claimer   ┃
  ┗━━━━━━━━━━━━━━━━━━━━━━━━━┛\n"""

def main():
    title = "Ave X Launcher - Casino Rain Claimer"
    os.system(f"title {title}")

    bypass_env = os.environ.get("RAIN_BYPASS")
    solver_env = os.environ.get("RAIN_SOLVER")
    site_env = os.environ.get("RAIN_SITE")

    bypass_choice = bypass_env if bypass_env else "none"
    solver_choice = solver_env if solver_env else "2captcha"
    website_choice = site_env if site_env else "HarvesterGG"

    bypass_label = "Camoufox CF Bypasser" if bypass_choice == "camoufox_solver" else "Sin Bypasser"
    solver_label = "2Captcha Solver" if solver_choice == "2captcha" else "Camoufox Local Solver"

    title += f" - [{bypass_label}] - [{solver_label}] - [{website_choice}]"
    os.system(f"title {title}")
    clear_header(SUB_TITLE)

    script_path = os.path.join(SRC_DIR, "modules", "casino_rain_claimer.py")
    if os.path.exists(script_path):
        run_script(script_path, bypass_choice, solver_choice, website_choice)
    else:
        console.print(f"[ERROR] No se encontró: {script_path}", style=ERROR_COLOR)
        time.sleep(2)

if __name__ == "__main__":
    main()
