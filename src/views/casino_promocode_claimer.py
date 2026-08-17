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

    while True:
        try:
            clear_header(SUB_TITLE)

            if bypass_env:
                bypass_choice = bypass_env
                bypass_label = "Camoufox CF Bypasser" if bypass_choice == "camoufox_solver" else "Sin Bypasser"
            else:
                choice_option = show_menu([
                    ("1", "Cloudflare Bypasser (Nodriver Headed)"),
                    ("2", "Sin Bypasser"),
                    ("0", "Regresar"),
                ], "Elige un método de bypass")

                if choice_option == "0":
                    sys.exit()
                elif choice_option in ["1", "2"]:
                    bypass_choice = "camoufox_solver" if choice_option == "1" else "none"
                    bypass_label = "Camoufox CF Bypasser" if choice_option == "1" else "Sin Bypasser"
                else:
                    time.sleep(0.8)
                    console.print(f"[ERROR] Opción {choice_option} no válida.", style=ERROR_COLOR)
                    time.sleep(2)
                    continue

            title += f" - [{bypass_label}]"
            os.system(f"title {title}")
            script_path = os.path.join(SRC_DIR, "modules", "casino_promocode_claimer.py")

            if site_env:
                website_choice = site_env
            else:
                clear_header()
                choice_site = show_menu([
                    ("1", "MM2WILD"),
                    ("2", "HarvesterGG"),
                ], "Elige un sitio")

                if choice_site in ["1", "2"]:
                    website_choice = "MM2WILD" if choice_site == "1" else "HarvesterGG"
                else:
                    time.sleep(0.8)
                    console.print(f"[ERROR] Opción {choice_site} no válida.", style=ERROR_COLOR)
                    time.sleep(2)
                    continue

            title += f" - [{website_choice}]"
            os.system(f"title {title}")
            clear_header(SUB_TITLE)

            if os.path.exists(script_path):
                run_script(script_path, bypass_choice, website_choice)
            else:
                time.sleep(0.8)
                console.print(f"[ERROR] No se encontró: {script_path}", style=ERROR_COLOR)
                time.sleep(2)

        except Exception as e:
            console.print(f"[PYTHON ERROR] {e}", style=ERROR_COLOR)
            time.sleep(3)

if __name__ == "__main__":
    main()
