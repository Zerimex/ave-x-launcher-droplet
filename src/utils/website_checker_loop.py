import asyncio
import json
import random
import requests
import time
from apscheduler.schedulers.background import BackgroundScheduler

from src.config import USERDATA, BLACKLIST_TEMP
from src.utils.helpers import refresh_userdata, save_userdata, log_status, get_user_config, build_proxy_params

scheduler = BackgroundScheduler()


async def trigger_bypass(acc_name, current_website, proxy):
    try:
        config = get_user_config()
        host = config.get("socket_host", "127.0.0.1")
        port = config.get("socket_port", 65432)
        reader, writer = await asyncio.open_connection(host, port)
        payload = {
            "siteurl": "https://mm2wild.com" if current_website == "MM2WILD" else "https://harvester.gg",
            "account": acc_name,
            "proxy": proxy,
            "website": current_website,
        }
        writer.write(json.dumps(payload).encode('utf-8'))
        await writer.drain()
        data = json.loads((await reader.read(4096)).decode('utf-8'))
        writer.close()
        await writer.wait_closed()

        ok = data.get("status") == "success"
        if ok:
            refresh_userdata()
            USERDATA.setdefault("cookies.txt", {})[acc_name] = data["cf_clearance"]
            save_userdata("cookies.txt", USERDATA["cookies.txt"])
        log_status(True, "SISTEMA", f"Bypass {'exitoso' if ok else 'falló'} para: {acc_name}.", "", "success" if ok else "error")
        return ok
    except Exception as e:
        log_status(True, "CRITICAL ERROR", f"Error conectando al servidor bypass: {e}", "", "error")
        return False


def try_refresh_account(nom, tok, is_mm2, uas, cookies, proxies_dict, current_website):
    success_acc = False
    cf_bypass = False
    fail_reason = "cf_clearance vencido"

    for acctry in range(1, 4):
        try:
            if is_mm2:
                h = {"authorization": f"Bearer {tok}", "origin": "https://mm2wild.com", "referer": "https://mm2wild.com/", "user-agent": uas.get(nom, "")}
                payload = {"deviceFingerprint": USERDATA.get("fingerprints.txt", {}).get(nom, "")}
            else:
                h = {"token": tok, "user-agent": uas.get(nom, ""), "origin": "https://harvester.gg", "referer": "https://harvester.gg/"}
                payload = None

            c = {"cf_clearance": cookies.get(nom, "")}
            p_params = build_proxy_params(proxies_dict.get(nom, ""))

            url = "https://api.mm2wild.com/auth/refreshTokens" if is_mm2 else "https://harvester.gg/"
            kwargs = {"headers": h, "cookies": c, "proxies": p_params, "timeout": 10}
            if payload is not None:
                kwargs["json"] = payload

            response = getattr(requests, "post" if is_mm2 else "get")(url, **kwargs)

            if response.status_code in [200, 201]:
                if is_mm2:
                    data = response.json()
                    new_access, new_refresh = data.get("accessToken"), data.get("refreshToken")
                    if new_access and new_refresh:
                        USERDATA.setdefault("refreshtokens.txt", {})[nom] = new_refresh
                        USERDATA.setdefault("authorizations.txt", {})[nom] = new_access
                log_status(True, "REFRESH", f"{nom}: OK (Intento {acctry})", "", "normal")
                success_acc = True
                break

            cf_triggers = (403, 401) if is_mm2 else (403,)
            if response.status_code in cf_triggers or "cloudflare" in response.text.lower():
                if acctry == 3:
                    cf_bypass = True

            log_status(True, "ERROR REFRESH", f"{nom}: Status {response.status_code} (Intento {acctry}/3)", "", "error")
        except Exception:
            if acctry == 3:
                fail_reason = "error de red/proxy"
            log_status(True, "ERROR REFRESH", f"{nom}: Error de red (Intento {acctry}/3)", "", "error")
        
        time.sleep(2)

    return success_acc, cf_bypass, fail_reason


def refresh_accounts(bypass_config, current_website):
    is_mm2 = (current_website == "MM2WILD")
    
    try:
        refresh_userdata()
        tokens = USERDATA.get("refreshtokens.txt" if is_mm2 else "authorizations.txt", {})
        uas = USERDATA.get("useragents.txt", {})
        cookies = USERDATA.get("cookies.txt", {})
        proxies_dict = USERDATA.get("proxies.txt", {})

        if not tokens:
            log_status(True, "ERROR REFRESH", "No se encontraron datos en los archivos .txt", "", "error")
            return

        list_accs = list(tokens.items())
        random.shuffle(list_accs)

        for nom, tok in list_accs:
            success_acc, cf_bypass, fail_reason = try_refresh_account(nom, tok, is_mm2, uas, cookies, proxies_dict, current_website)

            if success_acc:
                if nom in BLACKLIST_TEMP and BLACKLIST_TEMP[nom] in ["cf_clearance vencido", "error de red/proxy"]:
                    BLACKLIST_TEMP.pop(nom, None)
                    log_status(True, "SISTEMA", f"{nom}: Removido de la lista negra.", nom, "success")

            else:
                if nom not in BLACKLIST_TEMP:
                    BLACKLIST_TEMP[nom] = fail_reason
                    log_status(True, "ERROR REFRESH", f"{nom}: Añadido a la lista negra por {fail_reason}.", nom, "error")

            if cf_bypass and not success_acc and bypass_config != "none":
                log_status(True, "ERROR REFRESH", f"{nom}: 3 fallos seguidos. Solicitando bypass...", "", "error")
                if asyncio.run(trigger_bypass(nom, current_website, proxies_dict.get(nom, ""))):
                    refresh_userdata()
                    new_c = USERDATA.get("cookies.txt", {})
                    cookies[nom] = new_c.get(nom, cookies.get(nom, ""))
                    if is_mm2:
                        new_auth = USERDATA.get("authorizations.txt", {})
                        new_refresh = USERDATA.get("refreshtokens.txt", {})
                        USERDATA.setdefault("refreshtokens.txt", {})[nom] = new_refresh.get(nom, tok)
                        USERDATA.setdefault("authorizations.txt", {})[nom] = new_auth.get(nom, USERDATA.get("authorizations.txt", {}).get(nom, ""))
                    log_status(True, "SISTEMA", f"{nom}: Credenciales guardadas con éxito.", "", "success")

                    refresh_userdata()
                    uas = USERDATA.get("useragents.txt", {})
                    cookies = USERDATA.get("cookies.txt", {})
                    proxies_dict = USERDATA.get("proxies.txt", {})
                    retry_tok = USERDATA.get("refreshtokens.txt", {}).get(nom, tok) if is_mm2 else tok
                    time.sleep(10)
                    retry_ok, _, _ = try_refresh_account(nom, retry_tok, is_mm2, uas, cookies, proxies_dict, current_website)
                    if retry_ok:
                        success_acc = True
                        if nom in BLACKLIST_TEMP:
                            BLACKLIST_TEMP.pop(nom, None)
                            log_status(True, "SISTEMA", f"{nom}: Removido de la lista negra.", "", "success")

        if is_mm2:
            save_userdata("refreshtokens.txt", USERDATA.get("refreshtokens.txt", {}))
            save_userdata("authorizations.txt", USERDATA.get("authorizations.txt", {}))

    except Exception as e:
        log_status(True, "CRITICAL ERROR", f"Error crítico en la ejecución del refresh: {e}", "", "error")

        
def start_website_checker(current_website, bypass_config):
    scheduler.remove_all_jobs()

    scheduler.add_job(refresh_accounts, 'interval', minutes=25, misfire_grace_time=30, args=[bypass_config, current_website])
    scheduler.add_job(refresh_accounts, 'date', args=[bypass_config, current_website])
    
    if not scheduler.running:
        scheduler.start()
