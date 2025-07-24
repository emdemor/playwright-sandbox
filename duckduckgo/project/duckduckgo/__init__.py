import asyncio
from typing import Literal, Optional
from urllib.parse import quote_plus, urlencode

import bs4
from bs4 import BeautifulSoup
from loguru import logger
from playwright.async_api import async_playwright
from pydantic import BaseModel
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .browser import navigate_with_retry, set_browser, set_context, set_page
from .clear_html import clear_html_for_llm
from .proxies import get_proxy


class SearchResult(BaseModel):
    search_type: Literal["web", "news", "images", "videos"]
    link: str | None = None
    title: str | None = None
    snippet: str | None = None
    source: str | None = None
    relative_time: str | None = None


class UnexpectedDuckDuckGoError(Exception):
    pass


class ParseWebArticleError(Exception):
    def __init__(self, article: bs4.element.Tag):
        message = f"It was not possible to parse article \n```{article}```"
        super().__init__(message)


class ParseNewsArticleError(Exception):
    def __init__(self, article: bs4.element.Tag):
        message = f"It was not possible to parse article \n```{article}```"
        super().__init__(message)


async def search(
    query: str,
    search_type: str | list[str],
    use_proxy: bool = True,
    region: str | None = "br-pt",
    site: str | None = None,
) -> list[SearchResult]:

    if site:
        logger.info(f"Restricting the search to the website: '{site}'")
        query = f"site:{site} {query}"

    if isinstance(search_type, str):
        search_type = [search_type]

    async def process_search_type(_type: str):
        url = create_url(query, search_type=_type, region=region)
        logger.info(f"Generated url: '{url}'")
        proxy_config = (await get_proxy(test=False)) if use_proxy else None
        html_content = await _get_search_html(url, proxy_config=proxy_config)
        articles = await _get_articles_from_html(_type, html_content)
        result = await _parse_articles(_type, articles=articles)
        return result

    # Executa todas as tarefas em paralelo
    tasks = [process_search_type(_type) for _type in search_type]
    results_lists = await asyncio.gather(*tasks)

    # Combina todos os resultados
    results = []
    for result_list in results_lists:
        results.extend(result_list)

    return results


def print_retry_attempt(retry_state):
    print(
        f"Retry {retry_state.attempt_number} - Erro: {retry_state.outcome.exception()}"
    )
    print(f"Aguardando {retry_state.next_action.sleep:.1f} segundos...")


def print_final_result(retry_state):
    if retry_state.outcome.failed:
        print(f"Falha final após {retry_state.attempt_number} tentativas")
    else:
        print(f"Sucesso na tentativa {retry_state.attempt_number}")


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=2, max=10),
    retry=retry_if_exception_type((UnexpectedDuckDuckGoError)),
    before_sleep=print_retry_attempt,
    after=print_final_result,
    reraise=True,
)
async def _get_search_html(
    url,
    proxy_config=None,
    engine="firefox",
    timeouts=[60000, 90000, 120000],
    wait_time=0,
):
    async with async_playwright() as playwright:
        browser = await set_browser(playwright, engine=engine, proxy=proxy_config)
        context = await set_context(browser)
        page = await set_page(context)

        strategies = ["networkidle", "domcontentloaded", "load"]
        await navigate_with_retry(
            page, url, timeouts=timeouts, strategy_priority=strategies
        )

        await asyncio.sleep(wait_time)

        html_content = await page.content()

        if "Unexpected error" in html_content:
            raise UnexpectedDuckDuckGoError("Unexpected DuckDuckGo Error.")

        return html_content


async def _parse_single_web_article(article: bs4.element.Tag) -> list[SearchResult]:
    """Processa um único artigo de forma assíncrona"""
    try:
        links = article.find_all("a", {"data-testid": "result-extras-url-link"})
        links = [link.find("div").text for link in links]

        titles = article.find_all("a", {"data-testid": "result-title-a"})
        titles = [title.find("span").text for title in titles]

        snippets = article.find_all("div", {"data-result": "snippet"})
        snippets = [snippet.find("span").text for snippet in snippets]

        source = [
            p.text
            for d1 in article.find_all("div")
            for d2 in d1.find_all("div")
            for d3 in d2.find_all("div")
            for p in d3.find_all("p")
            if not len(p.find_all("span"))
        ]

        result = [
            SearchResult(search_type="web", link=lks, title=t, snippet=s1, source=s2)
            for lks, t, s1, s2 in zip(links, titles, snippets, source)
        ]

        return result
    except Exception as err:
        raise ParseWebArticleError(article) from err


async def _parse_web_articles(articles: list[bs4.element.Tag]) -> list[SearchResult]:
    article_results = await asyncio.gather(
        *[_parse_single_web_article(article) for article in articles]
    )
    results = []
    for article_result in article_results:
        results.extend(article_result)

    return results


async def _parse_single_news_article(
    article: bs4.element.Tag,
) -> Optional[SearchResult]:
    """Processa um único artigo de notícia de forma assíncrona"""
    try:
        # Extração do link
        try:
            tags_a = article.find_all("a")
            link = tags_a[0].get("href")
        except IndexError:
            link = None

        # Extração do título
        try:
            tags_h2 = article.find_all("h2")
            title = tags_h2[0].text
        except IndexError:
            title = None

        # Extração da fonte
        try:
            tags_span = article.find_all("span")
            source = tags_span[0].text
        except IndexError:
            source = None

        # Extração do tempo relativo
        try:
            divs_with_text = [
                div
                for div in article.find_all("div")
                if not div.find_all() and div.get_text(strip=True)
            ]
            times = [div.text for div in divs_with_text if "ago" in str(div)]
            relative_time = times[0]
        except IndexError:
            relative_time = None

        # Extração do snippet
        try:
            tags_p = article.find_all("p")
            snippet = tags_p[0].text
        except IndexError:
            snippet = None

        result = SearchResult(
            search_type="news",
            link=link,
            title=title,
            source=source,
            snippet=snippet,
            relative_time=relative_time,
        )

        # Retorna o resultado apenas se tiver link
        return result if result.link else None

    except Exception as err:
        raise ParseNewsArticleError(article) from err


async def _parse_news_articles(articles: list[bs4.element.Tag]) -> list[SearchResult]:
    """Processa todos os artigos de notícia de forma paralela usando asyncio.gather()"""

    article_results = await asyncio.gather(
        *[_parse_single_news_article(article) for article in articles],
        return_exceptions=True,
    )

    # Filtra resultados válidos e trata exceções
    results = []
    for result in article_results:
        if isinstance(result, Exception):
            logger.warning(f"Erro ao processar artigo: {result}")
            continue
        elif result is not None:  # Resultado válido com link
            results.append(result)

    return results


async def _parse_articles(
    search_type: str, articles: list[bs4.element.Tag]
) -> list[dict[str, str]]:
    match search_type:
        case "web":
            return await _parse_web_articles(articles)
        case "news":
            return await _parse_news_articles(articles)
        case "videos":
            raise NotImplementedError("Search of videos is not implemented yet.")
        case "images":
            raise NotImplementedError("Search of images is not implemented yet.")
        case _:
            raise ValueError(f"Search of '{search_type}' not recognized.")


async def _get_articles_from_html(
    search_type: str, html_content: str
) -> list[bs4.element.Tag]:
    clean_html = (await clear_html_for_llm(html_content))["cleaned_html"]
    soup = BeautifulSoup(clean_html, "html.parser")

    match search_type:
        case "web":
            return soup.find_all("article")
        case "news":
            return [
                article
                for article in soup.find_all("article")
                if not len(article.find_all("article"))
            ]
        case "videos":
            raise NotImplementedError("Search of videos is not implemented yet.")
        case "images":
            raise NotImplementedError("Search of images is not implemented yet.")
        case _:
            raise ValueError(f"Search of '{search_type}' not recognized.")


def create_url(
    query,
    # Configurações principais
    region: str | None = "br-pt",  # kl - ex: 'us-en', 'br-pt', 'uk-en'
    safe_search=None,  # kp - 1 (Strict), -1 (Moderate), -2 (Off)
    # Tipo de busca
    search_type=None,  # 'web', 'images', 'videos', 'news'
    # Configurações úteis
    instant_answers=None,  # kz - 1 (On), -1 (Off)
    new_window=None,  # kn - 1 (On), -1 (Off)
    full_urls: int | None = 1,  # kaf - 1 (On), -1 (Off)
    # Privacidade
    redirect=None,  # kd - 1 (On), -1 (Off)
    advertisements: int | None = -1,  # k1 - 1 (on), -1 (off)
):
    """
    Formata uma URL para pesquisa no DuckDuckGo com parâmetros essenciais.

    Args:
        query (str): Termos de busca
        region (str): Região da pesquisa (ex: 'us-en', 'br-pt', 'uk-en')
        safe_search (int): Filtro de conteúdo adulto (1=Strict, -1=Moderate, -2=Off)
        search_type (str): Tipo de busca ('web', 'images', 'videos', 'news')
        instant_answers (int): Respostas instantâneas (1=On, -1=Off)
        new_window (int): Abrir links em nova janela (1=On, -1=Off)
        full_urls (int): Mostrar URLs completas (1=On, -1=Off)
        redirect (int): Redirecionamento (1=On, -1=Off)
        advertisements (int): Anúncios (1=on, -1=off)

    Returns:
        str: URL formatada para o DuckDuckGo
    """
    base_url = "https://duckduckgo.com/"

    # Parâmetros básicos obrigatórios
    params = {"q": query}

    # Mapeamento dos parâmetros essenciais
    param_map = {
        "kl": region,
        "kp": safe_search,
        "kz": instant_answers,
        "kn": new_window,
        "kaf": full_urls,
        "kd": redirect,
        "k1": advertisements,
    }

    # Adicionar apenas parâmetros que não são None
    for param_key, param_value in param_map.items():
        if param_value is not None:
            params[param_key] = param_value

    # Configurar tipo de busca
    if search_type:
        if search_type.lower() == "images":
            params["iax"] = "images"
            params["ia"] = "images"
        elif search_type.lower() == "videos":
            params["iax"] = "videos"
            params["ia"] = "videos"
        elif search_type.lower() == "news":
            params["iar"] = "news"
            params["ia"] = "news"
        else:  # web ou qualquer outro valor
            params["ia"] = "web"
            params["t"] = "h_"
    elif len(params) == 1:  # apenas 'q' está presente
        # Padrão para busca web
        params["ia"] = "web"
        params["t"] = "h_"

    # Formatar URL com encoding adequado
    query_string = urlencode(params, safe=":", quote_via=quote_plus)
    return f"{base_url}?{query_string}"


def craete_duckduckgo_url(
    query,
    # Result Settings
    region=None,  # kl - ex: 'us-en', 'br-pt', 'uk-en'
    safe_search=None,  # kp - 1 (Strict), -1 (Moderate), -2 (Off)
    instant_answers=None,  # kz - 1 (On), -1 (Off)
    auto_load_images=None,  # kc - 1 (On), -1 (Off)
    auto_load_results=None,  # kav - 1 (On), -1 (Off)
    new_window=None,  # kn - 1 (On), -1 (Off)
    favicons=None,  # kf - 1 (On), -1 (Off)
    full_urls=None,  # kaf - 1 (On), -1 (Off)
    auto_suggest=None,  # kac - 1 (On), -1 (Off)
    # Privacy Settings
    redirect=None,  # kd - 1 (On), -1 (Off)
    https=None,  # kh - 1 (On), -1 (Off)
    address_bar=None,  # kg - 'p' (POST), 'g' (GET)
    video_playback=None,  # k5 - 1 (On), -1 (Off)
    # Color Settings
    header_color=None,  # kj - color code
    url_color=None,  # kx - color code
    background_color=None,  # k7 - color code
    text_color=None,  # k8 - color code
    link_color=None,  # k9 - color code
    visited_link_color=None,  # kaa - color code
    # Look & Feel Settings
    theme=None,  # kae - 'd' (dark), 'l' (light)
    size=None,  # ks - 's' (small), 'm' (medium), 'l' (large)
    width=None,  # kw - 'n' (normal), 'w' (wide)
    placement=None,  # km - 'l' (left), 'm' (center), 'r' (right)
    link_font=None,  # ka - 'p' (proxima nova), 's' (serif), 'o' (open sans)
    underline=None,  # ku - 1 (on), -1 (off)
    text_font=None,  # kt - 'p' (proxima nova), 's' (serif), 'o' (open sans)
    # Interface Settings
    header=None,  # ko - 1 (on), -1 (off), -2 (off with instant answers)
    advertisements=None,  # k1 - 1 (on), -1 (off)
    page_numbers=None,  # kv - 1 (on), -1 (off)
    units=None,  # kaj - 'm' (metric), 'i' (imperial)
    source=None,  # t - source identifier
    # Additional parameters
    ia=None,  # ia - instant answer type (web, images, videos, etc.)
    iax=None,  # iax - main search type (images, videos, etc.)
):
    """
    Formata uma URL para pesquisa no DuckDuckGo com parâmetros personalizáveis.

    Args:
        query (str): Termos de busca

        # Result Settings
        region (str): Região da pesquisa (ex: 'us-en', 'br-pt', 'uk-en')
        safe_search (int): Filtro de conteúdo adulto (1=Strict, -1=Moderate, -2=Off)
        instant_answers (int): Respostas instantâneas (1=On, -1=Off)
        auto_load_images (int): Carregamento automático de imagens (1=On, -1=Off)
        auto_load_results (int): Carregamento automático de resultados (1=On, -1=Off)
        new_window (int): Abrir links em nova janela (1=On, -1=Off)
        favicons (int): Mostrar favicons (1=On, -1=Off)
        full_urls (int): Mostrar URLs completas (1=On, -1=Off)
        auto_suggest (int): Sugestões automáticas (1=On, -1=Off)

        # Privacy Settings
        redirect (int): Redirecionamento (1=On, -1=Off)
        https (int): Forçar HTTPS (1=On, -1=Off)
        address_bar (str): Método da barra de endereços ('p'=POST, 'g'=GET)
        video_playback (int): Reprodução de vídeo (1=On, -1=Off)

        # Color Settings (códigos de cor hexadecimais)
        header_color (str): Cor do cabeçalho
        url_color (str): Cor das URLs
        background_color (str): Cor de fundo
        text_color (str): Cor do texto
        link_color (str): Cor dos links
        visited_link_color (str): Cor dos links visitados

        # Look & Feel Settings
        theme (str): Tema ('d'=dark, 'l'=light)
        size (str): Tamanho da interface ('s'=small, 'm'=medium, 'l'=large)
                   NOTA: Afeta o tamanho geral da interface, mas NÃO o tamanho dos snippets
        width (str): Largura ('n'=normal, 'w'=wide)
        placement (str): Posicionamento ('l'=left, 'm'=center, 'r'=right)
        link_font (str): Fonte dos links ('p'=proxima nova, 's'=serif, 'o'=open sans)
        underline (int): Sublinhado (1=on, -1=off)
        text_font (str): Fonte do texto ('p'=proxima nova, 's'=serif, 'o'=open sans)

        # Interface Settings
        header (int): Cabeçalho (1=on, -1=off, -2=off with instant answers)
        advertisements (int): Anúncios (1=on, -1=off)
        page_numbers (int): Números de página (1=on, -1=off)
        units (str): Unidades de medida ('m'=metric, 'i'=imperial)
        source (str): Identificador da fonte

        # Additional
        ia (str): Tipo de resposta instantânea ('web', 'images', 'videos', etc.)
        iax (str): Tipo principal de pesquisa ('images', 'videos', etc.)

    Returns:
        str: URL formatada para o DuckDuckGo
    """
    base_url = "https://duckduckgo.com/"

    # Parâmetros básicos obrigatórios
    params = {"q": query}

    # Adicionar parâmetros opcionais apenas se fornecidos
    param_map = {
        # Result Settings
        "kl": region,
        "kp": safe_search,
        "kz": instant_answers,
        "kc": auto_load_images,
        "kav": auto_load_results,
        "kn": new_window,
        "kf": favicons,
        "kaf": full_urls,
        "kac": auto_suggest,
        # Privacy Settings
        "kd": redirect,
        "kh": https,
        "kg": address_bar,
        "k5": video_playback,
        # Color Settings
        "kj": header_color,
        "kx": url_color,
        "k7": background_color,
        "k8": text_color,
        "k9": link_color,
        "kaa": visited_link_color,
        # Look & Feel Settings
        "kae": theme,
        "ks": size,
        "kw": width,
        "km": placement,
        "ka": link_font,
        "ku": underline,
        "kt": text_font,
        # Interface Settings
        "ko": header,
        "k1": advertisements,
        "kv": page_numbers,
        "kaj": units,
        "t": source,
        # Additional
        "ia": ia,
        "iax": iax,
    }

    # Adicionar apenas parâmetros que não são None
    for param_key, param_value in param_map.items():
        if param_value is not None:
            params[param_key] = param_value

    # Se não foi especificado 'ia' e não temos outros parâmetros específicos, usar 'web' como padrão
    if "ia" not in params and len(params) == 1:  # apenas 'q' está presente
        params["ia"] = "web"
        params["t"] = "h_"

    # Formatar URL com encoding adequado
    query_string = urlencode(params, safe=":", quote_via=quote_plus)

    return f"{base_url}?{query_string}"
