from rich.console import Console
from rich.text import Text
from datetime import datetime
import requests
import os
import time
import sys
import json
import subprocess

from src.config import ROOT_DIR, USERDATA_DIR, GLOBAL_USERDATA_FILES, USERDATA_FILES, USERDATA, ERROR_COLOR, SUCCESS_COLOR, PRIMARY_COLOR, ASCII_TITLE, DIV_TEXT

console = Console()


## FILES FUNCTIONS
def get_userdata_route(file, site=None):
    if file in GLOBAL_USERDATA_FILES:
        return os.path.join(USERDATA_DIR, file)
    
    if not site:
        site = [a for a in sys.argv if a in ["MM2WILD", "HarvesterGG"]][0]
    return os.path.join(USERDATA_DIR, site, file)

def get_userdata(file, site=None):
    res = {}
    route = get_userdata_route(file, site=site)
    if not os.path.exists(route): return res
    with open(route, "r", encoding="utf-8") as f:
        for n, l in enumerate(f, 1):
            l = l.strip()
            if not l: continue
            if ":" in l:
                k, v = l.split(":", 1)
                res[k.strip()] = v.strip()
    return res

def save_userdata(file, data, site=None):
    route = get_userdata_route(file, site=site)
    os.makedirs(os.path.dirname(route), exist_ok=True)
    with open(route, "w", encoding="utf-8") as f:
        for k, v in data.items():
            f.write(f"{k}:{v}\n")

def refresh_userdata():
    for f in USERDATA_FILES:
        USERDATA[f] = get_userdata(f)

def run_script(script_path, *args):
    env = os.environ.copy()
    env["PYTHONPATH"] = ROOT_DIR
    cmd = [sys.executable, script_path, *args]
    result = subprocess.run(cmd, env=env)
    if result.returncode != 0:
        print()
        console.print(
            f"[PYTHON ERROR] El módulo falló con código de salida {result.returncode}. "
            "Revisa el mensaje de error de arriba.",
            style=ERROR_COLOR
        )
        input("\nPresiona Enter para volver al menú...")
    return result.returncode

def verify_file_exists(website):
    files_data = {
        "proxies.txt": True, "useragents.txt": True,
        "authorizations.txt": False, "cookies.txt": True,
        "refreshtokens.txt": True, "fingerprints.txt": True
    }
    if website == "HarvesterGG":
        files_data = {k: v for k, v in files_data.items() if k in ["proxies.txt", "useragents.txt", "authorizations.txt", "cookies.txt", "users_id.txt", "last_rewards.txt"]}
        
    err_list = []
    for file, obligatorio in files_data.items():
        route = get_userdata_route(file)
        time.sleep(0.8)
        log_status(False, "SISTEMA", f"Archivo {'encontrado' if os.path.exists(route) else 'faltante'}: {file}", file, "normal" if os.path.exists(route) else "error")
        USERDATA[file] = get_userdata(file)
        if not USERDATA[file] and obligatorio:
            err_list.append(f"El archivo {website}/{file} está vacío.")

    if err_list:
        for err in err_list:
            time.sleep(0.8)
            log_status(False, "CRITICAL ERROR", err, "", "error")
        print()

        if os.name == "nt":
            log_status(False, "SISTEMA", "Presiona cualquier tecla para salir...", "", "normal")
            os.system("pause >nul")
            
        sys.exit()

    return True


## UI FUNCTIONS
def log_status(time_bool, script, message, key, status):
    STYLES = {
        "success": (SUCCESS_COLOR, SUCCESS_COLOR, SUCCESS_COLOR),
        "error": (ERROR_COLOR, ERROR_COLOR, ERROR_COLOR),
        "normal_success": (SUCCESS_COLOR, "default", PRIMARY_COLOR),
        "success_normal": (SUCCESS_COLOR, "default", PRIMARY_COLOR),
    }
    ps, ms, ks = STYLES.get(status, (PRIMARY_COLOR, "default", PRIMARY_COLOR))
    now = f"[{datetime.now().strftime('%H:%M:%S')}] " if time_bool else ""
    full_log = Text()
    full_log.append(f"{now}[{script}] ", style=ps)
    if key and key in message:
        izq, der = message.split(key, 1)
        full_log.append(izq, style=ms)
        full_log.append(key, style=ks)
        full_log.append(der, style=ms)
    else:
        full_log.append(message, style=ms)
    console.print(full_log)
    
def text_format(key, label, type="option"):
    if type == "option":
        sep = " » "
        end_sep = ""
    elif type == "input":
        sep = " "
        end_sep = " » "
    else:
        sep = " "
        end_sep = ""

    return Text.assemble(("[", PRIMARY_COLOR), key, ("]", PRIMARY_COLOR), f"{sep}{label}{end_sep}")

def clear_header(sub_title=None):
    os.system('cls' if os.name == 'nt' else 'clear')
    console.print(ASCII_TITLE, style=PRIMARY_COLOR)
    if sub_title:
        console.print(sub_title, style=PRIMARY_COLOR)
    console.print(DIV_TEXT, style=PRIMARY_COLOR)
    print()

def show_menu(options, prompt="Elige una opción"):
    for key, label in options:
        console.print(text_format(key, label, "option"))
    print()
    console.print(DIV_TEXT, style=PRIMARY_COLOR)
    print()
    return console.input(text_format("INPUT", prompt, "input")).strip()


## PROXY FUNCTIONS
def build_proxy_params(proxy_url):
    if not proxy_url or proxy_url.lower() == "local":
        return None
    if not proxy_url.startswith(("http://", "https://")):
        proxy_url = f"http://{proxy_url}"
    return {"http": proxy_url, "https": proxy_url}


## FUNCTIONS
def is_cloudflare_block(response):
    text = (response.text or "").lower().lstrip()
    content_type = (response.headers.get("content-type") or "").lower()
    is_html = text.startswith(("<!doctype", "<html")) or "text/html" in content_type
    cf_markers = (
        "just a moment" in text
        or "cf-chl" in text
        or "cf-browser-verification" in text
        or "challenge-platform" in text
        or "cf-mitigated" in text
        or "attention required" in text
        or "cloudflare ray id" in text
    )
    return response.status_code in (403, 503) and (is_html or cf_markers)

def send_claim(kind, source=None, code=None, amount=None, claimed_at=None, entries=None):
    config = get_user_config()
    api_key = config.get("finance_app_apikey", "")
    url = config.get("finance_app_url", "https://dashboard-casinos.lovable.app")
    if not api_key or "TU_CLAVE" in api_key or "..." in api_key or not url:
        return False
    if not entries:
        return False

    payload = {"kind": kind, "source": source, "entries": entries}
    if code is not None:
        payload["code"] = str(code)
    if isinstance(amount, (int, float)):
        payload["amount"] = amount
    if claimed_at:
        payload["claimed_at"] = claimed_at

    endpoint = f"{url.rstrip('/')}/api/public/claims"
    headers = {"content-type": "application/json", "x-api-key": api_key}

    for intento in range(3):
        try:
            r = requests.post(endpoint, headers=headers, json=payload, timeout=15)
            if r.status_code in (200, 201):
                return True
        except Exception:
            time.sleep(1)
    log_status(False, "DASHBOARD", "No se pudo enviar el claim tras 3 intentos.", "", "error")
    return False

def proxies_verify_status():
    refresh_userdata()
    
    proxies_list = USERDATA.get("proxies.txt", {})

    for nom, url in proxies_list.items():
        try:
            p_params = build_proxy_params(url)
            
            r = requests.get("https://api.ipify.org", proxies=p_params, timeout=5)
            time.sleep(0.2)
            log_status(False, "+", f"Proxy {nom} OK ({r.text})", "", "success")
        except Exception:
            time.sleep(0.3)
            log_status(False, "ERROR", f"Proxy {nom} no responde.", "", "error")

def get_user_config():
    route = os.path.join(ROOT_DIR, "userconfig.txt")
    config = {}
    try:
        with open(route, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                k, _, v = line.partition("=")
                k = k.strip().lower()
                v = v.strip()
                if v.lower() == "true":
                    v = True
                elif v.lower() == "false":
                    v = False
                else:
                    try:
                        v = int(v)
                    except ValueError:
                        try:
                            v = float(v)
                        except ValueError:
                            pass
                config[k] = v
    except FileNotFoundError:
        pass
    except Exception:
        pass
    override = os.environ.get("DOCKER_SOCKET_HOST")
    if override:
        config["socket_host"] = override
    return config
