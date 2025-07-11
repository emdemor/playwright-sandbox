import base64

from IPython.display import Image, display

from .browser import set_page


async def clear_headers(original_headers):
    """Limpa os headers mantendo apenas os campos necessários."""
    # Campos que consideramos necessários para a requisição
    necessary_fields = [
        "user-agent",
        "accept",
        "referer",
        "authorization",
        "origin",
        "host",
    ]

    # Cria um novo dicionário apenas com os campos necessários
    cleaned_headers = {
        k: v for k, v in original_headers.items() if k.lower() in necessary_fields
    }

    return cleaned_headers


async def perform_api_request(context, headers, endpoint):
    """Realiza uma requisição GET para o endpoint usando os headers fornecidos."""
    cleaned_headers = await clear_headers(headers)
    api_page = await set_page(context)
    try:
        response = await api_page.request.get(endpoint, headers=cleaned_headers)
        if response.ok:
            return await response.json()

        error_text = await response.text()
        print(f"Falha na requisição. Status: {response.status} | Erro: {error_text}")
        return None

    except Exception as e:
        print(f"Erro ao fazer a requisição: {str(e)}")
        return None
    finally:
        # Fecha a página da API
        await api_page.close()


def show_base64(base64_str: str):
    """Exibe uma imagem base64 no notebook Jupyter."""
    display(Image(data=base64.b64decode(base64_str)))
