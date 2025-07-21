import random

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .config import proxy_settings


class InvalidProxyError(Exception):
    pass


def get_masked_proxy(proxy_config):
    """Exibe configuração do proxy ocultando informações sensíveis"""
    server = proxy_config.get("server", "N/A")
    username = proxy_config.get("username", "N/A")
    password = proxy_config.get("password", "N/A")

    # Mascara o IP mantendo apenas os primeiros octetos
    def mask_server(server_url):
        import re

        # Substitui os dois últimos octetos do IP por ***
        return re.sub(r"(\d+\.\d+\.)\d+\.\d+", r"\1***.***", server_url)

    safe_server = mask_server(server) if server != "N/A" else "N/A"
    safe_username = (
        username[:3] + "*" * max(0, len(username) - 3) if username != "N/A" else "N/A"
    )
    safe_password = "*" * len(password) if password != "N/A" else "N/A"

    proxy_url = (
        f"http://{safe_username}:{safe_password}@{safe_server.replace('http://', '')}"
    )

    return proxy_url


def print_retry_attempt(retry_state):
    print(
        f"🔄 Retry {retry_state.attempt_number} - Erro: {retry_state.outcome.exception()}"
    )
    print(f"⏳ Aguardando {retry_state.next_action.sleep:.1f} segundos...")


def print_final_result(retry_state):
    if retry_state.outcome.failed:
        print(f"❌ Falha final após {retry_state.attempt_number} tentativas")
    else:
        print(f"✅ Sucesso na tentativa {retry_state.attempt_number}")


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=2, max=16),
    retry=retry_if_exception_type((InvalidProxyError)),
    before_sleep=print_retry_attempt,
    after=print_final_result,
    reraise=True,
)
async def get_proxy(test=False):
    with open(proxy_settings.proxies_file, "r") as f:
        lines = f.readlines()

    line = random.choice(lines).strip()
    ip, port, user, password = line.split(":")

    proxy_config = {
        "server": f"http://{ip}:{port}",
        "username": user,
        "password": password,
    }

    if test:
        try:
            await test_proxy(proxy_config)
        except Exception as err:
            raise InvalidProxyError("Invalid proxy config") from err

    return proxy_config


async def test_proxy(proxy_config):
    """Testa se o proxy está funcionando com múltiplos endpoints"""

    # Mascara o IP mantendo apenas os primeiros octetos
    def mask_server(server_url):
        import re

        # Substitui os dois últimos octetos do IP por ***
        return re.sub(r"(\d+\.\d+\.)\d+\.\d+", r"\1***.***", server_url)

    proxy_url = f"http://{proxy_config['username']}:{proxy_config['password']}@{proxy_config['server'].replace('http://', '')}"

    # Lista de endpoints para testar
    test_endpoints = [
        "http://httpbin.org/ip",
        "http://ipinfo.io/json",
        "https://api.ipify.org?format=json",
    ]

    async with httpx.AsyncClient(
        proxy=proxy_url,  # Mudança aqui: proxy ao invés de proxies
        timeout=httpx.Timeout(10.0, connect=5.0),
    ) as client:
        for endpoint in test_endpoints:
            try:
                response = await client.get(endpoint)

                if response.status_code == 200:
                    result = response.json()
                    ip = result.get("origin") or result.get("ip")

                    safe_server = mask_server(ip) if ip != "N/A" else "N/A"

                    print(
                        f"Proxy funcionando. IP: {safe_server} (testado em {endpoint})"
                    )
                    return True
                else:
                    print(
                        f"Endpoint {endpoint} retornou status: {response.status_code}"
                    )

            except httpx.TimeoutException:
                print(f"Timeout no endpoint {endpoint}")
                continue
            except httpx.ProxyError as e:
                print(f"Erro de proxy no endpoint {endpoint}: {e}")
                continue
            except Exception as e:
                print(f"Erro no endpoint {endpoint}: {e}")
                continue

    print("Proxy não funcionou em nenhum endpoint testado")
    return False
