import asyncio
import os
import sys
import time
import discord
import requests
import random

from src.config import USERDATA, USERDATA_DIR, BLACKLIST_TEMP
from src.utils.helpers import send_claim, log_status, refresh_userdata, proxies_verify_status, verify_file_exists, get_user_config, build_proxy_params, is_cloudflare_block
from src.utils.website_checker_loop import start_website_checker


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

BYPASS_CONFIG = sys.argv[1] if len(sys.argv) > 1 else "none"
CURRENT_WEBSITE = sys.argv[2] if len(sys.argv) > 2 else "none"

USER_CONFIG = get_user_config()


class MyClient(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def setup_hook(self):
        pass
    
    async def on_ready(self):
        print()
        log_status(False, "+", f"Bot conectado como {self.user}", f"{self.user}", "success_normal")
        print()
        
        try:
            start_website_checker(CURRENT_WEBSITE, BYPASS_CONFIG)
        except Exception as e:
            log_status(False, "CRITICAL ERROR", f"No se pudo iniciar el planificador de tareas: {e}", "", "error")

    async def on_message(self, message):
        triggers_channels = {
            "MM2WILD": {
                "channel_id": [1488177372418277527, 1492189165188550738],
                "trigger": 'Free Promo-code'
            },
            "HarvesterGG": {
                "channel_id": [1340813423696416850, 1484244769524682884, 1340813280213598218, 1462639491129938012, 1341925298920489042, 1355634312883470356, 1492189165188550738, 1512103890982801550],
                "trigger": ["```", "`"],
                "split_char": "-" 
            }
        }

        conf = triggers_channels.get(CURRENT_WEBSITE)
        if not conf or message.channel.id not in conf["channel_id"]:
            return

        promocode = None

        if CURRENT_WEBSITE == "MM2WILD" and conf["trigger"] in message.content:
            parts = message.content.split(conf["trigger"])
            if len(parts) >= 2:
                raw_data = parts[1]
                promocode = raw_data.replace('*', '').replace('"', '').strip()
                if " " in promocode:
                    promocode = promocode.split()[0]

        elif CURRENT_WEBSITE == "HarvesterGG":
            for t in conf["trigger"]:
                if t in message.content:
                    try:
                        msg = message.content.split(t)[1]
                        if conf["split_char"] in msg:
                            promocode = msg.split(conf["split_char"])[0]
                            break
                    except IndexError:
                        pass

        if promocode:
            promocode = promocode.replace("*", "").strip()
            if ":" in promocode:
                promocode = promocode.split(":")[-1].strip()
            if " " in promocode:
                promocode = promocode.split()[-1]
            promocode = promocode.strip()
                
            log_status(True, "SISTEMA", f"Código {CURRENT_WEBSITE} detectado en Discord: {promocode}", promocode, "normal")
            await self.automatic_claim(promocode)

    async def automatic_claim(self, promocode):
        refresh_userdata()
        p = USERDATA.get("proxies.txt", {})
        u = USERDATA.get("useragents.txt", {})
        a = USERDATA.get("authorizations.txt", {})
        c = USERDATA.get("cookies.txt", {})
        
        semaphore = asyncio.Semaphore(12)
        
        entradas = []
        
        async def account_process(nom, tok):
            async with semaphore:
                if CURRENT_WEBSITE == "HarvesterGG":
                    url_redeem = f"https://api.harvester.gg/api/v1/promo/activate?code={promocode}"
                    h = {
                        "user-agent": u.get(nom, ""), 
                        "origin": "https://harvester.gg", 
                        "referer": "https://harvester.gg"
                    }
                    cookies_list = {"token": tok, "cf_clearance": c.get(nom, "")}
                    req_method = requests.get
                    payload = None
                else:
                    url_redeem = "https://api.mm2wild.com/promocode/redeemPromocode"
                    h = {
                        "authorization": f"Bearer {tok}", 
                        "user-agent": u.get(nom, ""), 
                        "origin": "https://mm2wild.com", 
                        "referer": "https://mm2wild.com/"
                    }
                    cookies_list = {"cf_clearance": c.get(nom, "")}
                    req_method = requests.post
                    payload = {"code": promocode}

                proxy = p.get(nom, "")
                p_params = build_proxy_params(proxy)

                for acc_attempt in range(1, 4):
                    try:
                        r = await asyncio.to_thread(req_method, url_redeem, headers=h, cookies=cookies_list, proxies=p_params, json=payload, timeout=10)
                    except requests.exceptions.RequestException as e:
                        if acc_attempt < 3:
                            log_status(True, "ERROR", f"{nom}: Intento {acc_attempt}/3 fallido (Conexión/Proxy). Reintentando...", "", "normal")
                            continue
                        else:
                            log_status(True, "RED ERROR", f"{nom}: Error crítico tras 3 intentos.", "", "error")
                            entradas.append({"nickname": nom, "status": "Fallido"})
                            return False

                    if is_cloudflare_block(r):
                        log_status(True, "CRITICAL ERROR", f"{nom}: cf_clearance vencido/inválido (Status {r.status_code}).", "", "error")
                        entradas.append({"nickname": nom, "status": "Fallido"})
                        return False

                    try:
                        res_json = r.json() if r.text else {}
                    except ValueError:
                        snippet = (r.text or "")[:500]
                        log_status(True, "JSON ERROR", f"{nom}: Respuesta no es JSON válido (Status {r.status_code}). Sitio dice: {snippet}", "", "error")
                        entradas.append({"nickname": nom, "status": "Fallido"})
                        return False

                    if r.status_code in [200, 201]:
                        log_status(True, "SUCCESS", f"{nom}: {res_json}", "", "success")
                        entradas.append({"nickname": nom, "status": "Completado"})
                        return True

                    elif r.status_code == 500:
                        log_status(True, "SERVER ERROR", f"{nom} (500): {res_json}. Intento {acc_attempt}/3. Reintentando...", "", "normal")
                        if acc_attempt < 3:
                            continue
                        else:
                            entradas.append({"nickname": nom, "status": "Fallido"})
                            return False

                    elif r.status_code == 404:
                        log_status(True, "ERROR", f"{nom} (404): {res_json}", "", "error")

                    else:
                        log_status(True, "API INFO", f"{nom} ({r.status_code}): {res_json}", "", "normal")
                        entradas.append({"nickname": nom, "status": "Fallido"})
                        return False

        list_accs = list(a.items())
        random.shuffle(list_accs)

        if list_accs:
            accs = []
            for nom, tok in list_accs:
                if nom in BLACKLIST_TEMP:
                    motivo = BLACKLIST_TEMP[nom]
                    log_status(True, "BLACKLIST", f"{nom}: {motivo}.", "", "error")
                    continue
                
                accs.append(account_process(nom, tok))

            if accs:
                res = await asyncio.gather(*accs)
                success = res.count(True)
                faileds = res.count(False)
                print()
                log_status(False, "SISTEMA", f"Exitosos: {success} | Fallidos: {faileds}", "", "normal")
                if entradas:
                    send_claim("promocode", source=CURRENT_WEBSITE.lower(), code=promocode, entries=entradas)
            else:
                log_status(False, "SISTEMA", "Todas las cuentas disponibles están en blacklist temporal.", "", "normal")
        else:
            log_status(False, "ERROR", "No hay cuentas para procesar.", "", "error")

def main():
    try:       
        log_status(False, "+", f" {BASE_DIR}", "", "success")
        time.sleep(0.8)
        log_status(False, "+", f" {USERDATA_DIR}", "", "success")
        print()
        verify_file_exists(CURRENT_WEBSITE)
        proxies_verify_status()

        async def run_bot():
            async with MyClient() as client:
                await client.start(USER_CONFIG.get("discord_token", ""), reconnect=True)

        while True:
            try:
                asyncio.run(run_bot())
                log_status(False, "SISTEMA", "El bot se desconectó. Reconectando en 5 segundos...", "", "normal")
                time.sleep(5)
            except KeyboardInterrupt:
                log_status(False, "SISTEMA", "Detenido por el usuario.", "", "normal")
                break
            except Exception as e:
                log_status(False, "PYTHON ERROR", f"{e}", "", "error")
                log_status(False, "SISTEMA", "Conexión fallida. Reintentando en 30 segundos...", "", "normal")
                time.sleep(30)
    except Exception as e:
        log_status(False, "PYTHON ERROR", f"{e}", "", "error")
        time.sleep(5)

if __name__ == "__main__":
    main()
