import random

import httpx

from .config import proxy_settings


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


def get_proxy():
    with open(proxy_settings.proxies_file, "r") as f:
        lines = f.readlines()

    line = random.choice(lines).strip()
    ip, port, user, password = line.split(":")

    return {"server": f"http://{ip}:{port}", "username": user, "password": password}


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
