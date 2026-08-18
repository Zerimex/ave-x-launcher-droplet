import os
import sys

from src.config import ROOT_DIR, PRIMARY_COLOR, ASCII_TITLE, DIV_TEXT
from src.utils.helpers import console, text_format, run_script


def main():
    os.system("title Ave X Launcher")

    os.system('cls' if os.name == 'nt' else 'clear')
    console.print(ASCII_TITLE, style=PRIMARY_COLOR)
    console.print(text_format(".", "Launcher oficial especializado en la automatización 24/7."))
    console.print(text_format(".", "Version: 7.0 | Developed by AVERON LABS\n"))
    console.print(DIV_TEXT, style=PRIMARY_COLOR)
    print()

    module = os.environ.get("MODULE", "").lower()

    if module == "rain":
        bypass = os.environ.get("RAIN_BYPASS", "none")
        solver = os.environ.get("RAIN_SOLVER", "2captcha")
        site = os.environ.get("RAIN_SITE", "HarvesterGG")
        console.print(text_format(".", f"Bypass: {bypass} | Solver: {solver} | Sitio: {site}"))
        print()
        script_path = os.path.join(ROOT_DIR, "src", "views", "casino_rain_claimer.py")

    elif module == "promocode":
        bypass = os.environ.get("PROMOCODE_BYPASS", "none")
        site = os.environ.get("PROMOCODE_SITE", "MM2WILD")
        console.print(text_format(".", f"Bypass: {bypass} | Sitio: {site}"))
        print()
        script_path = os.path.join(ROOT_DIR, "src", "views", "casino_promocode_claimer.py")

    elif module == "local-server":
        script_path = os.path.join(ROOT_DIR, "src", "views", "local_server.py")

    else:
        console.print(f"[ERROR] MODULE no definido o inválido: '{module}'", style="#FF5E5E")
        sys.exit(1)

    if os.path.exists(script_path):
        run_script(script_path)
    else:
        console.print(f"[ERROR] No se encontró: {script_path}", style="#FF5E5E")
        sys.exit(1)


if __name__ == "__main__":
    main()
