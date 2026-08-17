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

    while True:
        try:
            clear_header(SUB_TITLE)

            if bypass_env:
                bypass_choice = bypass_env
                bypass_label = "Camoufox CF Bypasser" if bypass_choice == "camoufox_solver" else "Sin Bypasser"
            else:
                choice_bypass = show_menu([
                    ("1", "Cloudflare Bypasser (Nodriver Headed)"),
                    ("2", "Sin Bypasser"),
                ], "Elige un método de bypass")

                if choice_bypass in ["1", "2"]:
                    bypass_choice = "camoufox_solver" if choice_bypass == "1" else "none"
                    bypass_label = "Camoufox CF Bypasser" if choice_bypass == "1" else "Sin Bypasser"
                else:
                    console.print(f"[ERROR] Opción de Bypasser no válida.", style=ERROR_COLOR)
                    time.sleep(2)
                    continue

            title += f" - [{bypass_label}]"
            os.system(f"title {title}")

            if solver_env:
                solver_choice = solver_env
                solver_label = "2Captcha Solver" if solver_choice == "2captcha" else "Camoufox Local Solver"
            else:
                clear_header(SUB_TITLE)
                choice_solver = show_menu([
                    ("1", "2Captcha API"),
                    ("2", "Local Solver (Camoufox)"),
                ], "Elige un método para Captchas")

                if choice_solver in ["1", "2"]:
                    solver_choice = "2captcha" if choice_solver == "1" else "local_solver"
                    solver_label = "2Captcha Solver" if choice_solver == "1" else "Camoufox Local Solver"
                else:
                    console.print(f"[ERROR] Opción de Solucionador no válida.", style=ERROR_COLOR)
                    time.sleep(2)
                    continue

            title += f" - [{solver_label}]"
            os.system(f"title {title}")

            if site_env:
                website_choice = site_env
            else:
                clear_header(SUB_TITLE)
                choice_site = show_menu([
                    ("1", "HarvesterGG"),
                    ("2", "MM2WILD"),
                ], "Elige un sitio")

                if choice_site in ["1", "2"]:
                    website_choice = "HarvesterGG" if choice_site == "1" else "MM2WILD"
                else:
                    console.print(f"[ERROR] Opción {choice_site} no válida.", style=ERROR_COLOR)
                    time.sleep(2)
                    continue

            title += f" - [{website_choice}]"
            os.system(f"title {title}")
            clear_header(SUB_TITLE)

            script_path = os.path.join(SRC_DIR, "modules", "casino_rain_claimer.py")
            if os.path.exists(script_path):
                run_script(script_path, bypass_choice, solver_choice, website_choice)
            else:
                console.print(f"[ERROR] No se encontró: {script_path}", style=ERROR_COLOR)
                time.sleep(2)

        except Exception as e:
            console.print(f"[PYTHON ERROR] {e}", style=ERROR_COLOR)
            time.sleep(3)

if __name__ == "__main__":
    main()
