import os
import sys
import time

from src.config import ROOT_DIR, PRIMARY_COLOR, ERROR_COLOR, ASCII_TITLE, DIV_TEXT
from src.utils.helpers import console, text_format, show_menu, run_script


def main():
    os.system("title Ave X Launcher")

    auto = os.environ.get("AUTO_SELECT")
    views = {
        "1": "casino_promocode_claimer.py",
        "2": "casino_rain_claimer.py",
        "3": "local_server.py",
    }

    if auto and auto in views:
        script_path = os.path.join(ROOT_DIR, "src", "views", views[auto])
        if os.path.exists(script_path):
            run_script(script_path)
        return

    while True:
        try:
            os.system('cls' if os.name == 'nt' else 'clear')

            console.print(ASCII_TITLE, style=PRIMARY_COLOR)
            console.print(text_format(".", "Launcher oficial especializado en la automatización 24/7."))
            console.print(text_format(".", "Simplifica la interacción eliminando procesos manuales y mejorando la eficiencia.\n"))
            console.print(text_format(".", "Version: 7.0 | Developed by AVERON LABS\n"))
            
            console.print(DIV_TEXT, style=PRIMARY_COLOR)
            print()

            menu_options = [
                ("1", "Casino Promocode Claimer"),
                ("2", "Casino Rain Claimer"),
                ("3", "HTTP Local Server"),
            ]

            menu_options.append(("0", "Salir"))

            choice_option = show_menu(menu_options)

            if choice_option == "0":
                sys.exit()
            elif choice_option in views:
                script_path = os.path.join(ROOT_DIR, "src", "views", views[choice_option])
                if os.path.exists(script_path):
                    run_script(script_path)
                else:
                    time.sleep(0.8)
                    console.print(f"[ERROR] No se encontró: {script_path}", style=ERROR_COLOR)
                    time.sleep(2)
            else:
                time.sleep(0.8)
                console.print(f"[ERROR] Opción {choice_option} no válida.", style=ERROR_COLOR)
                time.sleep(2)

        except Exception as e:
            console.print(f"[PYTHON ERROR] {e}", style=ERROR_COLOR)
            time.sleep(3)

if __name__ == "__main__":
    main()
