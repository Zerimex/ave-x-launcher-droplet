import json
import os
import sys
import time
import asyncio
from camoufox import DefaultAddons
from camoufox.async_api import AsyncCamoufox

from src.config import ROOT_DIR, USERDATA_DIR
from src.utils.helpers import get_user_config, get_userdata, save_userdata, log_status


if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
config = get_user_config()


class SolverServer:

    HTML_TEMPLATE = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Boterdrop Solver</title>
        <script src="https://challenges.cloudflare.com/turnstile/v0/api.js?onload=onloadTurnstileCallback" async="" defer=""></script>
    </head>
    <body>
        <!-- cf turnstile -->
        <p id="ip-display"></p>
    </body>
    </html>
    """
    
    def __init__(self, headless: bool, thread: int, page_count: int, cleanup_interval_minutes: int, socket_host: str, socket_port: int, proxy_file: str = ""):
        self.headless = headless
        self.thread_count = thread
        self.page_count = page_count
        self.proxy_file = os.path.join(USERDATA_DIR, "proxies.txt")
        self.cleanup_interval_minutes = cleanup_interval_minutes
        self.socket_host = socket_host
        self.socket_port = socket_port
        self.page_pool = asyncio.Queue()
        self.browser_args = [
            "--no-sandbox",
            "--disable-setuid-sandbox",
        ]
        self.camoufox = None
        self.browser = None
        self.contexts = []
        self.proxies = []
        self._proxy_index = 0
        self.max_task_num = self.thread_count * self.page_count

    def _load_proxies(self):
        self.proxies = []
        locals_count = 0

        if not os.path.isfile(self.proxy_file):
            log_status(True, "SISTEMA", f"Archivo 'proxies.txt' no encontrado, usando IP local", "", "normal")
            return

        with open(self.proxy_file) as f:
            for ln in f:
                ln = ln.strip()
                if not ln or ln.startswith("#"):
                    continue
                proxy = ln.split(":", 1)[1].strip() if ":" in ln and not ln.startswith("http") else ln
                if proxy.lower() == "local":
                    locals_count += 1
                elif proxy:
                    self.proxies.append(proxy)

        total = len(self.proxies) + locals_count
        if total:
            detail = f"{len(self.proxies)} con proxy" + (f", {locals_count} Local" if locals_count else "")
            log_status(True, "SISTEMA", f"Cargando {total} proxies ({detail})", "", "normal")
        else:
            log_status(True, "SISTEMA", "proxies.txt vacío, usando IP local", "", "normal")
        print()

    def _next_proxy(self):
        if not self.proxies:
            return None
        proxy = self.proxies[self._proxy_index % len(self.proxies)]
        self._proxy_index += 1
        return proxy

    def _save_useragent(self, account: str, ua: str):
        data = get_userdata("useragents.txt")
        data[account] = ua
        save_userdata("useragents.txt", data)
        log_status(True, "SISTEMA", f"UserAgent guardado para {account}.", account, "success")

    async def _check_proxy_ip(self, context, proxy: str):
        try:
            page = await context.new_page()
            await page.goto("https://api.ipify.org", wait_until="domcontentloaded", timeout=15000)
            ip = await page.evaluate("document.body.innerText")
            ip = ip.strip() if ip else "desconocida"
            log_status(True, "+", f"Proxy {ip} OK", "", "success")
            await page.close()
        except Exception as e:
            log_status(True, "ERROR", f"No se pudo verificar IP para {proxy}: {e}", "", "error")

    async def _periodic_cleanup(self, interval_minutes: int):
        DRAIN_TIMEOUT = 60

        while True:
            await asyncio.sleep(interval_minutes * 60)
            print()
            log_status(True, "REFRESH", f"Iniciando refresh de proxies... (intervalo: {interval_minutes} min)", "", "normal")

            collected = []
            try:
                while True:
                    item = self.page_pool.get_nowait()
                    collected.append(item)
            except asyncio.QueueEmpty:
                pass

            busy_count = self.max_task_num - len(collected)

            if busy_count > 0:
                log_status(True, "ERROR", f"Esperando {busy_count} páginas en uso (máx {DRAIN_TIMEOUT}s)...", "", "error")
                deadline = time.time() + DRAIN_TIMEOUT
                while len(collected) < self.max_task_num and time.time() < deadline:
                    try:
                        remaining = deadline - time.time()
                        if remaining <= 0:
                            break
                        item = await asyncio.wait_for(
                            self.page_pool.get(), timeout=remaining
                        )
                        collected.append(item)
                    except asyncio.TimeoutError:
                        break

                still_busy = self.max_task_num - len(collected)
                if still_busy > 0:
                    log_status(True, "ERROR", f"{still_busy} páginas aún en uso tras timeout, forzando reinicio sin ellas.", "", "error")


            old_contexts = list(self.contexts)
            self.contexts = []

            for page, _ in collected:
                try:
                    await page.close()
                except Exception:
                    pass

            for context in old_contexts:
                try:
                    await context.close()
                except Exception:
                    pass

            stale = []
            try:
                while True:
                    stale.append(self.page_pool.get_nowait())
            except asyncio.QueueEmpty:
                pass
            if stale:
                log_status(True, "SERVIDOR", f"Cerrando {len(stale)} páginas obsoletas del pool.", "", "normal")
                for stale_page, _ in stale:
                    try:
                        await stale_page.close()
                    except Exception:
                        pass

            try:
                await self._build_page_pool()
                log_status(True, "SERVIDOR", f"Reinicio completo de contexts finalizado. ({self.page_pool.qsize()} páginas)", "", "success")
            except Exception as e:
                log_status(True, "CRITICAL ERROR", f"Error al reconstruir pool: {e}, intentando reiniciar navegador...", "", "error")
                try:
                    try:
                        await self.browser.close()
                    except Exception:
                        pass
                    self.browser = await self.camoufox.start()
                    await self._build_page_pool()
                    asyncio.sleep(2)
                    log_status(True, "SERVIDOR", f"Reinicio de navegador exitoso. ({self.page_pool.qsize()} páginas)", "", "success")
                except Exception as e2:
                    log_status(True, "CRITICAL ERROR", f"Error al reiniciar navegador: {e2}", "", "error")

    async def _solve_clearance_direct(self, url: str, proxy: str, account: str, timeout: int = 60):
        start_time = time.time()
        context = None
        page = None
        try:
            context_kwargs = {}

            if proxy and proxy.lower() != "local":
                log_status(True, "SERVIDOR", f"Usando proxy: {proxy}", "", "normal")
                from urllib.parse import urlparse
                parsed = urlparse(proxy)
                if parsed.scheme and parsed.hostname:
                    server = f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"
                    if parsed.username and parsed.password:
                        context_kwargs["proxy"] = {"server": server, "username": parsed.username, "password": parsed.password}
                    else:
                        context_kwargs["proxy"] = {"server": server}
            else:
                log_status(True, "SERVIDOR", "Sin proxy — usando IP local", "", "normal")

            context = await self.browser.new_context(**context_kwargs)
            page = await context.new_page()
            real_ua = await page.evaluate("navigator.userAgent")
            log_status(True, "SERVIDOR", f"User-Agent del navegador: {real_ua}", "", "normal")
            if account:
                self._save_useragent(account, real_ua)
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)

            deadline = time.time() + timeout
            cf_clearance = None
            waited = 0
            while time.time() < deadline:
                title = await page.title()
                cookies = await context.cookies()
                cf_cookie = next((c for c in cookies if c["name"] == "cf_clearance"), None)
                if cf_cookie and "just a moment" not in title.lower():
                    cf_clearance = cf_cookie["value"]
                    break
                await asyncio.sleep(1)
                waited += 1

            elapsed = round(time.time() - start_time, 3)

            if cf_clearance:
                log_status(True, "SERVIDOR", f"Challenge/Clearance obtenido con éxito. ({elapsed}s)", "", "success")
                return {"status": "success", "cf_clearance": cf_clearance}
            else:
                title_text = await page.title()
                log_status(True, "ERROR", f"El challenge solver falló.({timeout}s)", "", "error")
                return {"status": "error", "message": f"cf_clearance no encontrado después de {timeout}s. Título: '{title_text}'"}

        except Exception as e:
            elapsed = round(time.time() - start_time, 3)
            log_status(True, "CRITICAL ERROR", f"Clearance exception: {e}", "", "error")
            return {"status": "error", "message": str(e)}
        finally:
            if page:
                try:
                    await page.close()
                except Exception:
                    pass
            if context:
                try:
                    await context.close()
                except Exception:
                    pass

    async def _solve_turnstile_direct(self, url: str, sitekey: str, account: str, website: str, action: str = None):
        start_time = time.time()
        page, context = await self.page_pool.get()
        try:
            url_with_slash = url if url.endswith("/") else url + "/"
            turnstile_div = (
                f'<div class="cf-turnstile" style="background:white;" data-sitekey="{sitekey}"'
                + (f' data-action="{action}"' if action else "")
                + "></div>"
            )
            page_data = self.HTML_TEMPLATE.replace("<!-- cf turnstile -->", turnstile_div)

            try:
                await page.evaluate("() => { window.__debugErrors = []; window.onerror = (m,s,l,c,e) => { window.__debugErrors.push({msg:m,src:s,line:l,col:c}); }; }")
            except Exception:
                pass

            try:
                await page.unroute_all()
            except Exception:
                pass
            await page.route(url_with_slash, lambda route: route.fulfill(body=page_data, status=200))
            await page.goto(url_with_slash)
            await page.eval_on_selector("//div[@class='cf-turnstile']", "el => el.style.width = '70px'")

            for attempt in range(80):
                try:
                    value = await page.input_value("[name=cf-turnstile-response]", timeout=400)
                    if value == "":
                        await page.locator("//div[@class='cf-turnstile']").click(timeout=400)
                        await asyncio.sleep(0.3)
                    else:
                        elapsed = round(time.time() - start_time, 3)
                        log_status(True, "SERVIDOR", f"Captcha resuelto: {account} ({elapsed}s) [{website}]", "", "success")
                        return value
                except Exception as e:
                    pass

            log_status(True, "ERROR", "No se pudo resolver turnstile después de 80 intentos.", "", "error")
            return None
        except Exception as e:
            log_status(True, "CRITICAL ERROR", f"Turnstile exception: {e}", "", "error")
            return None
        finally:
            try:
                await page.unroute_all()
            except Exception:
                pass
            if context in self.contexts:
                await self.page_pool.put((page, context))
            else:
                log_status(True, "LOCAL SERVER", "Página descartada (context reiniciado)", "", "normal")

    async def _create_context_with_proxy(self, proxy: str = None):
        if not proxy:
            return await self.browser.new_context()
        from urllib.parse import urlparse
        parsed = urlparse(proxy)
        if not parsed.scheme or not parsed.hostname:
            log_status(True, "ERROR", f"Formato de proxy inválido: {proxy}", "", "error")
            return await self.browser.new_context()
        server = f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"
        if parsed.username and parsed.password:
            return await self.browser.new_context(
                proxy={"server": server, "username": parsed.username, "password": parsed.password}
            )
        return await self.browser.new_context(proxy={"server": server})

    async def _build_page_pool(self):
        self.contexts = []
        for _ in range(self.thread_count):
            proxy = self._next_proxy()
            context = await self._create_context_with_proxy(proxy)
            self.contexts.append(context)
            if proxy:
                asyncio.create_task(self._check_proxy_ip(context, proxy))
            for _ in range(self.page_count):
                page = await context.new_page()
                await self.page_pool.put((page, context))

    async def _handle_socket_requests(self, reader, writer):
        try:
            data = await asyncio.wait_for(reader.read(4096), timeout=30)
            payload = json.loads(data.decode("utf-8"))

            sitekey = payload.get("sitekey")
            account = payload.get("account")
            website = payload.get("website")
            siteurl = payload.get("siteurl")

            if sitekey:
                action = payload.get("captcha_action")
                log_status(True, "SERVIDOR", f"Petición de captcha: {account} [{website}]", website, "normal")
                await asyncio.sleep(0.8)

                if not siteurl:
                    response = {"status": "error", "message": "Faltan siteurl"}
                    writer.write(json.dumps(response).encode("utf-8"))
                    await writer.drain()
                    return

                token = await self._solve_turnstile_direct(siteurl, sitekey, account, website, action)
                if token:
                    response = {"status": "success", "token": token}
                else:
                    response = {"status": "error", "message": "No se pudo resolver el captcha"}
            else:
                proxy = payload.get("proxy")
                if not siteurl:
                    response = {"status": "error", "message": "Falta 'url' para clearance"}
                    writer.write(json.dumps(response).encode("utf-8"))
                    await writer.drain()
                    return
                if not proxy:
                    response = {"status": "error", "message": "Falta 'proxy' para clearance"}
                    writer.write(json.dumps(response).encode("utf-8"))
                    await writer.drain()
                    return

                print()
                log_status(True, "SERVIDOR", f"Petición de challenge/clearance: {account} [{website}]", website, "normal")
                response = await self._solve_clearance_direct(
                    url=siteurl,
                    proxy=proxy,
                    account=account,
                    timeout=payload.get("timeout", 60)
                )

            writer.write(json.dumps(response).encode("utf-8"))
            await writer.drain()
        except asyncio.TimeoutError:
            try:
                writer.write(json.dumps({"status": "error", "message": "timeout"}).encode("utf-8"))
                await writer.drain()
            except Exception:
                pass
        except Exception as e:
            log_status(True, "CRITICAL ERROR", f"Socket error: {e}", "", "error")
            try:
                writer.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
                await writer.drain()
            except Exception:
                pass
        finally:
            try:
                writer.close()
            except Exception:
                pass

    async def _start_socket_server(self):
        server = await asyncio.start_server(self._handle_socket_requests, self.socket_host, self.socket_port)
        log_status(True, "SERVIDOR", f"Servidor TCP escuchando en {self.socket_host}:{self.socket_port}", "", "success")
        async with server:
            await server.serve_forever()

    async def start(self):
        try:
            probe = await asyncio.start_server(lambda r, w: None, self.socket_host, self.socket_port)
            probe.close()
            await probe.wait_closed()
        except OSError:
            log_status(True, "CRITICAL ERROR", f"Puerto {self.socket_port} ya está en uso.", "", "error")
            time.sleep(0.8)
            print()
            log_status(True, "SISTEMA", "Presione cualquier tecla para regresar...", "", "normal")
            await asyncio.to_thread(os.system, "pause >nul")
            return False

        self._load_proxies()
        self.camoufox = AsyncCamoufox(
            headless=self.headless,
            exclude_addons=[DefaultAddons.UBO],
            args=self.browser_args
        )
        self.browser = await self.camoufox.start()
        await self._build_page_pool()
        asyncio.create_task(self._periodic_cleanup(self.cleanup_interval_minutes))
        asyncio.create_task(self._start_socket_server())
        return True


async def main():
    log_status(False, "+", ROOT_DIR, "", "success")
    time.sleep(0.8)
    log_status(False, "+", USERDATA_DIR, "", "success")
    time.sleep(0.8)
    print()
    
    required = ["headless", "thread", "page_count", "cleanup_interval_minutes", "socket_host", "socket_port"]
    missing = [k for k in required if k not in config or config[k] is None or (isinstance(config[k], str) and not config[k].strip())]
    if missing:
        time.sleep(0.8)
        log_status(True, "SISTEMA", f"Parámetros vacíos o faltantes en config: {', '.join(missing)}", "", "error")
        time.sleep(0.8)
        print()
        log_status(True, "SISTEMA", "Presione cualquier tecla para regresar...", "", "normal")
        await asyncio.to_thread(os.system, "pause >nul")
        return

    server = SolverServer(
        headless=config["headless"],
        thread=config["thread"],
        page_count=config["page_count"],
        cleanup_interval_minutes=config["cleanup_interval_minutes"],
        socket_host=config["socket_host"],
        socket_port=config["socket_port"],
    )

    log_status(True, "SISTEMA", f"Headless: {config['headless']}", str(config['headless']), "normal")
    time.sleep(0.8)
    log_status(True, "SISTEMA", f"Threads: {config['thread']}", str(config['thread']), "normal")
    time.sleep(0.8)
    log_status(True, "SISTEMA", f"Pages por thread: {config['page_count']}", str(config['page_count']), "normal")
    time.sleep(0.8)
    log_status(True, "SISTEMA", f"Cleanup interval: {config['cleanup_interval_minutes']} min", str(config['cleanup_interval_minutes']), "normal")
    time.sleep(0.8)
    log_status(True, "SISTEMA", f"Host: {config['socket_host']}", config['socket_host'], "normal")
    time.sleep(0.8)
    log_status(True, "SISTEMA", f"Port: {config['socket_port']}", str(config['socket_port']), "normal")
    time.sleep(0.8)

    if not await server.start():
        return

    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(main())
