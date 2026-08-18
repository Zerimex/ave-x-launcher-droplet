import asyncio
import os
import sys
import time
from datetime import datetime, timezone, timedelta
import socket
import requests
import random
import socketio
from twocaptcha import TwoCaptcha
import threading
import json

from src.config import USERDATA_DIR, USERDATA, WEBSITE_CONFIG, BLACKLIST_TEMP
from src.utils.helpers import log_status, send_claim, get_user_config, refresh_userdata, verify_file_exists, proxies_verify_status, build_proxy_params, is_cloudflare_block
from src.utils.website_checker_loop import start_website_checker, trigger_bypass


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

BYPASS_CONFIG = sys.argv[1]
SOLVER_TYPE = sys.argv[2]
CURRENT_WEBSITE = sys.argv[3]

USER_CONFIG = get_user_config()
APIKEY_2CAPTCHA = USER_CONFIG.get("2captcha_apikey", "")

URL_WEBSITE = WEBSITE_CONFIG[CURRENT_WEBSITE]["URL"]
WEBSITE_SITEKEY = WEBSITE_CONFIG[CURRENT_WEBSITE]["SITEKEY"]


class MM2WildWebsocketManager:
    def __init__(self, callback_on_rain):
        self.sio = None
        self.callback_on_rain = callback_on_rain
        self.rains_registradas = set()
        self.running = True

    def registrar_eventos(self):
        @self.sio.event
        def connect():
            print()
            log_status(False, "+", "Conectado al WebSocket (RainAlert) de MM2WILD con éxito.", "MM2WILD", "normal_success")
            print()
            self.sio.emit("init", {})

        @self.sio.on("init")
        def on_init(data):
            log_status(False, "SISTEMA", "Handshake 'init' completado en WS.", "", "normal")

        @self.sio.on("rain.onUpdate")
        def on_rain_update(data):
            if data is None:
                return

            rain_id = data.get("rainId")
            state = data.get("state")
            distributed_at_str = data.get("distributedAt")
            rain_pot = data.get("prize") if data.get("prize") is not None else data.get("amount", "???")

            if not rain_id:
                return

            if state == "SCHEDULED" and rain_id not in self.rains_registradas:
                self.rains_registradas.add(rain_id)
                
                if distributed_at_str:
                    target_time = datetime.fromisoformat(distributed_at_str.replace("Z", "+00:00"))
                    now_utc = datetime.now(timezone.utc)
                    segundos = (target_time - now_utc).total_seconds() - 80
                    
                    if segundos > 0:
                        tiempo_final = datetime.now() + timedelta(seconds=segundos)
                        timeout_formateado = tiempo_final.strftime('%Y-%m-%d %H:%M:%S')
                        print()
                        log_status(True, "SISTEMA", f"RAIN: {rain_id} | POT: {rain_pot} | Timeout: {timeout_formateado}", str(rain_id), "normal")
                        print()
                        self.callback_on_rain(rain_id, segundos, rain_pot)
                        return
                    else:
                        print()
                        log_status(True, "SISTEMA", f"Comenzando rain (Inicio inmediato): {rain_id} | POT: {rain_pot}", str(rain_id), "success_normal")
                        print()
                        self.callback_on_rain(rain_id, 0, rain_pot)
                        return

            elif state == "OPEN":
                if rain_id in self.rains_registradas:
                    return
                self.rains_registradas.add(rain_id)
                print()
                log_status(True, "SISTEMA", f"Comenzando rain: {rain_id} | POT: {rain_pot}", str(rain_id), "success_normal")
                print()
                self.callback_on_rain(rain_id, 0, rain_pot)

    def iniciar_bucle(self):
        intentos_fallidos = 0
        
        while self.running:
            refresh_userdata()
            tokens = USERDATA.get("authorizations.txt", {})
            uas = USERDATA.get("useragents.txt", {})
            cookies = USERDATA.get("cookies.txt", {})
            proxies_dict = USERDATA.get("proxies.txt", {})

            if not tokens:
                log_status(True, "WS ERROR", "No hay cuentas en authorizations.txt.", "", "error")
                time.sleep(20)
                continue

            nom_ref = random.choice(list(tokens.keys()))
            ua_ref = uas.get(nom_ref, "")
            cookie_ref = cookies.get(nom_ref, "")
            proxy_url = proxies_dict.get(nom_ref, "")

            try:    
                session = requests.Session()
                
                if proxy_url and proxy_url.lower() != "local":
                    session.proxies = build_proxy_params(proxy_url)
                
                session.headers.update({
                    "User-Agent": ua_ref,
                    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
                    "Cache-Control": "no-cache",
                    "Pragma": "no-cache"
                })

                self.sio = socketio.Client(http_session=session)
                self.registrar_eventos()

                self.sio.connect(
                    url="https://api.mm2wild.com",
                    socketio_path="/socket.io/",
                    transports=["websocket"],
                    headers={
                        "Origin": "https://mm2wild.com",
                        "User-Agent": ua_ref,
                        "Cookie": f"cf_clearance={cookie_ref}"
                    },
                    namespaces=["/"]
                )
                
                intentos_fallidos = 0
                
                while self.sio.connected and self.running:
                    time.sleep(5)
                    
                log_status(True, "SISTEMA", "Se perdió la conexión con el WS de MM2WILD. Intentando reconexión...", "", "error")

            except Exception as e:
                intentos_fallidos += 1
                log_status(True, "WS ERROR", f"Fallo en WS con {nom_ref}: {e}. Intentos: {intentos_fallidos}/3", "", "error")
                
                try:
                    if self.sio:
                        self.sio.disconnect()
                except:
                    pass

                if intentos_fallidos >= 3:
                    print()
                    log_status(False, "SISTEMA", "Máximo de intentos seguidos alcanzado. Posible caducidad general de cookies.", "", "error")
                    log_status(False, "SISTEMA", "Esperando 5 minutos en modo de espera antes de volver a rotar cuentas...", "", "normal")
                    print()
                    time.sleep(300)
                    intentos_fallidos = 0
                    continue
                
                time.sleep(15)


class RainClaimerManager:
    def __init__(self):
        self.loop = None
        self.is_running = True

    async def start(self):
        self.loop = asyncio.get_running_loop()

        try:
            start_website_checker(CURRENT_WEBSITE, BYPASS_CONFIG)
        except Exception as e:
            log_status(False, "CRITICAL ERROR", f"No se pudo iniciar el planificador de tareas: {e}", "", "error")

        if CURRENT_WEBSITE == "MM2WILD":
            threading.Thread(target=self.proceso_websocket_mm2wild, daemon=True).start()
        elif CURRENT_WEBSITE == "HarvesterGG":
            self.loop.create_task(self.harvester_rains_manager())

        while self.is_running:
            await asyncio.sleep(1)

    def proceso_websocket_mm2wild(self):
        ws_manager = MM2WildWebsocketManager(callback_on_rain=self.alerta_desde_websocket)
        ws_manager.iniciar_bucle()

    def alerta_desde_websocket(self, rain_id, segundos_espera, rain_pot):
        if self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self.gestionar_y_canjear(rain_id, segundos_espera, rain_pot), 
                self.loop
            )

    async def gestionar_y_canjear(self, rain_id, segundos_espera, rain_pot=None):
        if segundos_espera > 0:
            await asyncio.sleep(segundos_espera)
        await self.canjear_auto(rain_id, rain_pot)

    async def harvester_rains_manager(self):
        intentos_fallidos = 0   
        
        while CURRENT_WEBSITE == "HarvesterGG" and self.is_running:
            refresh_userdata()
            tokens = USERDATA.get("authorizations.txt", {})
            uas = USERDATA.get("useragents.txt", {})
            cookies = USERDATA.get("cookies.txt", {})
            proxies_dict = USERDATA.get("proxies.txt", {})

            if not tokens:
                await asyncio.sleep(20)
                continue

            nom_ref = random.choice(list(tokens.keys()))
            tok_ref = tokens[nom_ref]

            try:
                url_rains = "https://api.harvester.gg/api/v1/rains"
                headers = {
                    "user-agent": uas.get(nom_ref, ""),
                    "origin": "https://harvester.gg",
                    "referer": "https://harvester.gg/",
                    "token": tok_ref
                }
                cookies_dict = {"cf_clearance": cookies.get(nom_ref, "")}
                
                proxy_url = proxies_dict.get(nom_ref, "")
                p_params = build_proxy_params(proxy_url)
                
                response = await asyncio.to_thread(
                    requests.get, url_rains, headers=headers, cookies=cookies_dict, proxies=p_params, timeout=10
                )

                if response.status_code == 200:
                    intentos_fallidos = 0   
                    data = response.json()
                    rain_id = data.get("id")
                    rain_pot = data.get("pot")
                    time_stage_str = data.get("estimatedFinishTimeStage")

                    if time_stage_str and rain_id:
                        target_time = datetime.fromisoformat(time_stage_str.replace("Z", "+00:00"))
                        now_utc = datetime.now(timezone.utc)

                        target_time_utc4 = target_time - timedelta(hours=4)
                        time_stage_utc4 = target_time_utc4.strftime('%Y-%m-%d %H:%M:%S')

                        segundos_para_empezar = (target_time - now_utc).total_seconds()

                        if segundos_para_empezar > 0:
                            print()
                            log_status(True, "SISTEMA", f"RAIN: {rain_id} | POT: {rain_pot} | Timeout: {time_stage_utc4}", "", "normal")
                            print()
                            await asyncio.sleep(segundos_para_empezar)
                            
                        print()
                        log_status(True, "SISTEMA", f"Comenzando rain: {rain_id}", rain_id, "success_normal")
                        print()
                        await self.canjear_auto(rain_id, rain_pot)
                        await asyncio.sleep(180)
                    else:
                        log_status(True, "ERROR", "El JSON recibido no contiene los parámetros esperados.", "", "error")
                        await asyncio.sleep(30)
                else:
                    if is_cloudflare_block(response) and BYPASS_CONFIG != "none":
                        log_status(True, "CLEARANCE ERROR", f"{nom_ref}: cf_clearance vencido/inválido (Status {response.status_code}). Solicitando bypass...", "", "error")
                        proxy_url = proxies_dict.get(nom_ref, "")
                        bypass_ok = await trigger_bypass(nom_ref, CURRENT_WEBSITE, proxy_url)
                        if bypass_ok:
                            intentos_fallidos = 0
                            await asyncio.sleep(10)
                            continue
                    intentos_fallidos += 1
                    log_status(True, "ERROR", f"Status {response.status_code} al revisar lloviznas con {nom_ref}. Intentos: {intentos_fallidos}/3.", "", "error")
                    await asyncio.sleep(30)

            except Exception as e:
                intentos_fallidos += 1
                log_status(True, "ERROR", f"Error en administrador de lloviznas con {nom_ref}: {e}. Intentos: {intentos_fallidos}/3.", "", "error")
                if intentos_fallidos >= 3:
                    print()
                    log_status(False, "SISTEMA", "Presiona cualquier tecla para regresar...", "", "normal")
                    await asyncio.to_thread(os.system, "pause >nul")
                    self.close()   
                    return
                await asyncio.sleep(30)
                
    def close(self):
        self.is_running = False

    async def canjear_auto(self, id_reclamar, rain_pot=None):
        refresh_userdata()
        p, u, a, c = USERDATA.get("proxies.txt", {}), USERDATA.get("useragents.txt", {}), USERDATA.get("authorizations.txt", {}), USERDATA.get("cookies.txt", {})
        
        semaforo = asyncio.Semaphore(12)        

        # --- INTEGRACIÓN CON LOCAL SOLVER / 2CAPTCHA ---
        def resolver_turnstile_sync(sitekey_actual, URL, acc_name, action_actual=None):
            if SOLVER_TYPE == "local_solver":
                config_local = get_user_config()
                SOCKET_HOST = config_local.get("socket_host", "127.0.0.1")
                SOCKET_PORT = config_local.get("socket_port", 65432)
                
                payload = {
                    "sitekey": sitekey_actual,
                    "siteurl": URL,
                    "captcha_action": action_actual,
                    "account": acc_name,
                    "website": CURRENT_WEBSITE,
                }
                
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.connect((SOCKET_HOST, SOCKET_PORT))
                        s.sendall(json.dumps(payload).encode('utf-8'))
                        
                        data = s.recv(4096).decode('utf-8')
                        if not data:
                            raise RuntimeError("El servidor central cerró la conexión sin responder.")
                        
                        res = json.loads(data)
                        if res.get("status") == "success":
                            return res.get("token")
                        else:
                            raise RuntimeError(res.get("message", "Error desconocido del Solver"))
                            
                except Exception as e:
                    raise RuntimeError(f"Fallo de conexión con Local Solver: {e}")
            else:
                # 2Captcha original
                solver = TwoCaptcha(APIKEY_2CAPTCHA)
                kwargs = {
                    "sitekey": sitekey_actual,
                    "url": URL
                }
                if action_actual:
                    kwargs["action"] = action_actual
                    
                result = solver.turnstile(**kwargs)
                return result['code']

        lista_cuentas = list(a.items())
        total_cuentas = len(lista_cuentas)
        random.shuffle(lista_cuentas)

        entradas = []

        async def accounts_claim(nom, tok, indice_cuenta, rain_pot=None):
            async with semaforo:
                is_harvester = (CURRENT_WEBSITE == "HarvesterGG")
                API_JOINRAIN = f"https://api.harvester.gg/api/v1/rains/join/{id_reclamar}" if is_harvester else "https://api.mm2wild.com/rain/joinRain"
                WEBSITE_PAGEACTION = None if is_harvester else "joinRain"
                
                async def obtener_captcha_token():
                    for i in range(3):
                        try:
                            token = await asyncio.to_thread(resolver_turnstile_sync, WEBSITE_SITEKEY, URL_WEBSITE, nom, WEBSITE_PAGEACTION)
                            if token: return token
                        except Exception as e:
                            log_status(True, "CAPTCHA ERROR", f"{nom}: Fallo ({SOLVER_TYPE}) ({i+1}/3): {e}", "", "error")
                            await asyncio.sleep(2)
                    return None

                delay_base = 1 + (indice_cuenta * (3 / max(1, total_cuentas - 1))) if total_cuentas > 1 else 1
                await asyncio.sleep(max(1, delay_base + random.uniform(-1, 1)))

                h = {'User-Agent': u.get(nom, ""), 'Accept': 'application/json', 'Origin': URL_WEBSITE, 'Referer': URL_WEBSITE}
                cookies_dict = {"cf_clearance": c.get(nom, "")}
                
                if is_harvester:
                    cookies_dict["token"] = tok
                else:
                    h["Authorization"] = f"Bearer {tok}"

                proxy = p.get(nom, "")
                p_params = build_proxy_params(proxy)

                for intento in range(1, 3):
                    if intento == 1 or 'token_captcha' not in locals() or not token_captcha:
                        token_captcha = await obtener_captcha_token()
                        if not token_captcha:
                            log_status(True, "CAPTCHA ERROR", f"{nom}: Abortando por falta de Captcha.", "", "error")
                            entradas.append({"nickname": nom, "status": "Fallido"})
                            return False

                    payload = {"turnstileToken": token_captcha} if is_harvester else {"captcha": token_captcha}

                    try:
                        r = await asyncio.to_thread(requests.post, API_JOINRAIN, headers=h, cookies=cookies_dict, proxies=p_params, json=payload, timeout=12)
                    except requests.exceptions.RequestException as e:
                        if intento == 1:
                            log_status(True, "ERROR", f"{nom}: Fallo de Red/Proxy. Reintentando de inmediato con el mismo captcha...", "", "normal")
                            await asyncio.sleep(1)
                            continue
                        log_status(True, "RED ERROR", f"{nom}: Error crítico tras reintento. Detalle: {e}", "", "error")
                        entradas.append({"nickname": nom, "status": "Fallido"})
                        return False

                    if is_cloudflare_block(r):
                        if BYPASS_CONFIG != "none":
                            log_status(True, "CLEARANCE ERROR", f"{nom}: cf_clearance vencido/inválido (Status {r.status_code}). Solicitando bypass...", "", "error")
                            proxy_url = proxies_dict.get(nom, "")
                            bypass_ok = await trigger_bypass(nom, CURRENT_WEBSITE, proxy_url)
                            if bypass_ok:
                                refresh_userdata()
                                cookies_dict["cf_clearance"] = USERDATA.get("cookies.txt", {}).get(nom, "")
                                log_status(True, "CLEARANCE", f"{nom}: Cookie actualizada. Reintentando...", "", "normal")
                                await asyncio.sleep(3)
                                continue
                        log_status(True, "CLEARANCE ERROR", f"{nom}: cf_clearance vencido/inválido (Status {r.status_code}).", "", "error")
                        entradas.append({"nickname": nom, "status": "Fallido"})
                        return False

                    try:
                        res_json = r.json() if r.text else {}
                    except ValueError as e:
                        snippet = (r.text or "")[:500]
                        log_status(True, "ERROR", f"{nom}: Respuesta no es JSON válido (Status {r.status_code}). Sitio dice: {snippet}", "", "error")
                        if intento == 1:
                            await asyncio.sleep(1)
                            continue
                        entradas.append({"nickname": nom, "status": "Fallido"})
                        return False

                    if r.status_code in [200, 201]:
                        log_status(True, "API", f"{nom}: {res_json}", "", "success")
                        entradas.append({"nickname": nom, "status": "Completado"})
                        return True
                    
                    error_msg = res_json.get('error', '') if isinstance(res_json, dict) else ''
                    text_msg = res_json.get('message', '') if isinstance(res_json, dict) else ''

                    es_error_captcha = (not is_harvester and error_msg == 'CaptchaFailed') or (is_harvester and "captcha" in str(text_msg).lower())
                    if es_error_captcha and intento == 1:
                        log_status(True, "API ERROR", f"{nom}: Captcha inválido. Regenerando token...", "", "error")
                        token_captcha = None 
                        continue

                    if error_msg == 'UserBlockedFromChatRain':
                        BLACKLIST_TEMP[nom] = "baneado de chat/rain"
                        log_status(True, "BLACKLIST", f"{nom}: baneado de chat/rain.", nom, "error")
                        entradas.append({"nickname": nom, "status": "Fallido"})
                        return False

                    log_status(True, "API INFO", f"{nom} ({r.status_code}): {res_json}", "", "normal")
                    entradas.append({"nickname": nom, "status": "Fallido"})
                    return False

        if lista_cuentas:
            tareas = []
            for idx, (nom, tok) in enumerate(lista_cuentas):
                if nom in BLACKLIST_TEMP:
                    motivo = BLACKLIST_TEMP[nom]
                    log_status(True, "BLACKLIST", f"{nom}: {motivo}.", "", "error")
                    entradas.append({"nickname": nom, "status": "Fallido"})
                    continue
            
                tareas.append(accounts_claim(nom, tok, idx, rain_pot))
                
            if tareas:
                res = await asyncio.gather(*tareas)
                exitos = res.count(True)
                fallidos = res.count(False)
                print()
                log_status(False, "SISTEMA", f"Exitosos: {exitos} | Fallidos: {fallidos}", "", "normal")
            else:
                log_status(False, "SISTEMA", "Todas las cuentas disponibles están en blacklist.", "", "normal")

            if entradas:
                claimed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                send_claim("rain", source=CURRENT_WEBSITE.lower(), code=id_reclamar, amount=rain_pot, claimed_at=claimed_at, entries=entradas)
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

        manager = RainClaimerManager()
        asyncio.run(manager.start())
        
    except Exception as e:
        log_status(False, "PYTHON ERROR", f"{e}", "", "error")
        time.sleep(5)

if __name__ == "__main__":
    main()
