import re

from bs4 import BeautifulSoup, Comment


async def clean_html_for_llm(
    html_content,
    preserve_structure=True,
    max_length=None,
    remove_classes=True,
    keep_semantic_attrs=False,
):
    """
    Limpa HTML removendo elementos desnecessários para análise organizacional
    por LLM.

    Args:
        html_content (str): HTML bruto da página
        preserve_structure (bool): Se deve manter estrutura semântica básica
        max_length (int): Tamanho máximo do HTML limpo (opcional)
        remove_classes (bool): Se deve remover atributos class de todas as tags
        keep_semantic_attrs (bool): apenas atributos semânticos essenciais

    Returns:
        dict: {
            'cleaned_html': str,
            'original_size': int,
            'cleaned_size': int,
            'compression_ratio': float,
            'removed_elements': dict
        }
    """

    original_size = len(html_content)
    removed_elements = {
        "comments": 0,
        "scripts": 0,
        "styles": 0,
        "svgs": 0,
        "base64_images": 0,
        "meta_tags": 0,
        "hidden_elements": 0,
        "ads_trackers": 0,
        "classes_removed": 0,
        "attributes_removed": 0,
    }

    # 1. Parse HTML com BeautifulSoup
    soup = BeautifulSoup(html_content, "html.parser")

    # 2. Remover comentários HTML
    comments = soup.find_all(string=lambda text: isinstance(text, Comment))
    for comment in comments:
        comment.extract()
        removed_elements["comments"] += 1

    # 3. Remover scripts e seus conteúdos
    scripts = soup.find_all(["script", "noscript"])
    for script in scripts:
        script.decompose()
        removed_elements["scripts"] += 1

    # 4. Remover estilos CSS
    styles = soup.find_all(["style", "link"])
    for style in styles:
        # Manter apenas link rel="canonical" e similares importantes
        if style.name == "link":
            rel = style.get("rel", [])
            if isinstance(rel, str):
                rel = [rel]
            if not any(r in ["canonical", "alternate", "shortlink"] for r in rel):
                style.decompose()
                removed_elements["styles"] += 1
        else:
            style.decompose()
            removed_elements["styles"] += 1

    # 5. Remover SVGs completos
    svgs = soup.find_all("svg")
    for svg in svgs:
        svg.decompose()
        removed_elements["svgs"] += 1

    # 6. Remover imagens base64 e otimizar tags img
    images = soup.find_all("img")
    for img in images:
        src = img.get("src", "")

        # Remover imagens base64
        if src.startswith("data:image"):
            img.decompose()
            removed_elements["base64_images"] += 1
        else:
            # Manter apenas atributos essenciais das imagens
            essential_attrs = ["src", "alt", "title", "class", "id"]
            for attr in list(img.attrs.keys()):
                if attr not in essential_attrs:
                    del img[attr]

    # 7. Remover meta tags desnecessárias
    meta_tags = soup.find_all("meta")
    for meta in meta_tags:
        name = meta.get("name", "").lower()
        property_attr = meta.get("property", "").lower()

        # Manter apenas meta tags importantes para SEO/estrutura
        important_meta = [
            "description",
            "keywords",
            "author",
            "robots",
            "og:title",
            "og:description",
            "og:type",
            "twitter:title",
            "twitter:description",
        ]

        if name not in important_meta and property_attr not in important_meta:
            meta.decompose()
            removed_elements["meta_tags"] += 1

    # 8. Remover elementos ocultos
    hidden_selectors = [
        '[style*="display:none"]',
        '[style*="display: none"]',
        '[style*="visibility:hidden"]',
        '[style*="visibility: hidden"]',
        ".hidden",
        ".d-none",
        ".sr-only",
        ".screen-reader-text",
    ]

    for selector in hidden_selectors:
        hidden_elements = soup.select(selector)
        for element in hidden_elements:
            element.decompose()
            removed_elements["hidden_elements"] += len(hidden_elements)

    # 9. Remover elementos de tracking e publicidade
    ad_tracking_selectors = [
        '[class*="google-ad"]',
        '[class*="advertisement"]',
        '[class*="banner"]',
        '[id*="google_ads"]',
        '[class*="tracking"]',
        '[class*="analytics"]',
        'iframe[src*="google"]',
        'iframe[src*="facebook"]',
        'iframe[src*="twitter"]',
        '[class*="social-share"]',
    ]

    for selector in ad_tracking_selectors:
        try:
            elements = soup.select(selector)
            for element in elements:
                element.decompose()
                removed_elements["ads_trackers"] += len(elements)
        except Exception as err:
            print(err)
            continue

    # 10. Limpar atributos desnecessários de todos os elementos
    for element in soup.find_all():
        if element.name:
            if keep_semantic_attrs:
                # Modo conservador: apenas atributos realmente semânticos
                essential_attrs = [
                    "id",
                    "href",
                    "src",
                    "alt",
                    "title",
                    "role",
                    "aria-label",
                    "aria-labelledby",
                ]
            else:
                # Modo padrão: manter alguns atributos úteis para análise
                essential_attrs = [
                    "id",
                    "href",
                    "src",
                    "alt",
                    "title",
                    "role",
                    "aria-label",
                    "aria-labelledby",
                    "type",
                    "name",
                    "value",
                ]

            # Remover classes se solicitado
            if remove_classes and "class" in element.attrs:
                del element["class"]
                removed_elements["classes_removed"] += 1

            # Remover outros atributos não essenciais
            attrs_to_remove = []
            for attr in list(element.attrs.keys()):
                # Manter data-* attributes que podem ter informações úteis
                if attr.startswith("data-"):
                    continue

                if attr not in essential_attrs:
                    # Se não removeu classes, manter 'class'
                    if not remove_classes and attr == "class":
                        continue
                    attrs_to_remove.append(attr)

            for attr in attrs_to_remove:
                del element[attr]
                removed_elements["attributes_removed"] += 1

    # 11. Simplificar estrutura se necessário
    if preserve_structure:
        cleaned_html = _preserve_semantic_structure(soup)
    else:
        cleaned_html = _extract_text_content(soup)

    # 12. Limpar espaços em branco excessivos
    cleaned_html = _clean_whitespace(cleaned_html)

    # 13. Truncar se necessário
    if max_length and len(cleaned_html) > max_length:
        cleaned_html = _smart_truncate(cleaned_html, max_length)

    cleaned_size = len(cleaned_html)
    compression_ratio = (original_size - cleaned_size) / original_size * 100

    return {
        "cleaned_html": cleaned_html,
        "original_size": original_size,
        "cleaned_size": cleaned_size,
        "compression_ratio": compression_ratio,
        "removed_elements": removed_elements,
        "savings_kb": (original_size - cleaned_size) / 1024,
    }


def _preserve_semantic_structure(soup):
    """
    Preserva apenas elementos semânticos importantes para análise
    organizacional
    """
    # Elementos importantes para estrutura organizacional
    important_elements = [
        "html",
        "head",
        "body",
        "title",
        "header",
        "nav",
        "main",
        "section",
        "article",
        "aside",
        "footer",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "p",
        "div",
        "span",
        "a",
        "ul",
        "ol",
        "li",
        "table",
        "thead",
        "tbody",
        "tr",
        "td",
        "th",
        "form",
        "input",
        "button",
        "select",
        "option",
        "img",
        "figure",
        "figcaption",
    ]

    # Remover elementos não importantes
    for element in soup.find_all():
        if element.name and element.name not in important_elements:
            # Preservar o conteúdo text, mas remover a tag
            element.unwrap()

    return str(soup)


def _extract_text_content(soup):
    """
    Extrai apenas conteúdo textual organizado
    """
    # Elementos que devem ter quebras de linha
    block_elements = ["p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "tr"]

    for element in soup.find_all(block_elements):
        element.append("\n")

    # Extrair texto e manter estrutura mínima
    text_content = soup.get_text(separator=" ", strip=True)
    return text_content


def _clean_whitespace(html_content):
    """
    Remove espaços em branco excessivos mantendo legibilidade
    """
    # Remover múltiplas quebras de linha
    html_content = re.sub(r"\n\s*\n\s*\n", "\n\n", html_content)

    # Remover espaços múltiplos
    html_content = re.sub(r" {2,}", " ", html_content)

    # Remover tabs e espaços no início/fim das linhas
    lines = html_content.split("\n")
    cleaned_lines = [line.strip() for line in lines if line.strip()]

    return "\n".join(cleaned_lines)


def _smart_truncate(html_content, max_length):
    """
    Trunca HTML de forma inteligente preservando estrutura
    """
    if len(html_content) <= max_length:
        return html_content

    # Tentar truncar em uma tag completa
    truncated = html_content[:max_length]

    # Encontrar última tag completa
    last_tag_end = truncated.rfind(">")
    if last_tag_end > max_length * 0.8:  # Se perdemos menos de 20%
        truncated = truncated[: last_tag_end + 1]

    return truncated + "\n<!-- [TRUNCATED] -->"


def analyze_html_structure(html_content):
    """
    Analisa a estrutura do HTML para otimizar limpeza
    """
    soup = BeautifulSoup(html_content, "html.parser")

    analysis = {
        "total_elements": len(soup.find_all()),
        "scripts": len(soup.find_all("script")),
        "styles": len(soup.find_all(["style", "link"])),
        "images": len(soup.find_all("img")),
        "svgs": len(soup.find_all("svg")),
        "forms": len(soup.find_all("form")),
        "tables": len(soup.find_all("table")),
        "links": len(soup.find_all("a")),
        "headings": len(soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])),
        "semantic_elements": len(
            soup.find_all(
                ["header", "nav", "main", "section", "article", "aside", "footer"]
            )
        ),
        "base64_images": len(
            [
                img
                for img in soup.find_all("img")
                if img.get("src", "").startswith("data:image")
            ]
        ),
        "comments": len(soup.find_all(string=lambda text: isinstance(text, Comment))),
    }

    return analysis


def clean_html_ultra_minimal(html_content):
    """
    Limpeza ultra-minimalista mantendo apenas estrutura semântica pura
    Remove TODAS as classes, IDs e atributos não-essenciais
    """
    soup = BeautifulSoup(html_content, "html.parser")

    # Remover tudo desnecessário primeiro
    for element in soup.find_all(["script", "style", "svg", "noscript"]):
        element.decompose()

    # Remover comentários
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()

    # Remover imagens base64
    for img in soup.find_all("img"):
        if img.get("src", "").startswith("data:image"):
            img.decompose()

    # Limpeza radical de atributos - manter APENAS os essenciais para semântica
    for element in soup.find_all():
        if element.name:
            # Atributos permitidos por tipo de elemento
            allowed_attrs = {
                "a": ["href"],
                "img": ["src", "alt"],
                "input": ["type", "name", "value"],
                "form": ["action", "method"],
                "table": [],
                "th": [],
                "td": [],
                "tr": [],
                "ul": [],
                "ol": [],
                "li": [],
                "div": [],
                "span": [],
                "p": [],
                "h1": [],
                "h2": [],
                "h3": [],
                "h4": [],
                "h5": [],
                "h6": [],
                "header": [],
                "nav": [],
                "main": [],
                "section": [],
                "article": [],
                "aside": [],
                "footer": [],
            }

            # Manter apenas atributos permitidos para este elemento
            element_allowed = allowed_attrs.get(element.name, [])

            # Remover todos os atributos exceto os permitidos
            attrs_to_remove = []
            for attr in list(element.attrs.keys()):
                if attr not in element_allowed:
                    attrs_to_remove.append(attr)

            for attr in attrs_to_remove:
                del element[attr]

    # Limpar espaços em branco excessivos
    cleaned_html = _clean_whitespace(str(soup))

    return cleaned_html


def clean_html_structure_only(html_content):
    """
    Mantém apenas a estrutura de navegação e links importantes
    Ideal para análise de organização do site
    """
    soup = BeautifulSoup(html_content, "html.parser")

    # Elementos importantes para navegação e estrutura
    important_selectors = [
        "nav",
        "header",
        "footer",
        "main",
        "aside",
        "a[href]",
        "form",
        "input",
        "button",
        "select",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "ul",
        "ol",
        "li",
        "table",
        "tr",
        "td",
        "th",
    ]

    # Criar novo soup apenas com elementos importantes
    new_soup = BeautifulSoup("<html><body></body></html>", "html.parser")
    body = new_soup.find("body")

    for selector in important_selectors:
        elements = soup.select(selector)
        for element in elements:
            # Clonar elemento removendo atributos desnecessários
            new_element = new_soup.new_tag(element.name)

            # Manter apenas href para links e alguns atributos essenciais
            if element.name == "a" and element.get("href"):
                new_element["href"] = element["href"]
            elif element.name in ["input", "button"] and element.get("type"):
                new_element["type"] = element["type"]
            elif element.name == "form" and element.get("action"):
                new_element["action"] = element["action"]

            # Adicionar texto do elemento
            text_content = element.get_text(strip=True)
            if text_content:
                new_element.string = text_content

            body.append(new_element)

    return str(new_soup)


def clean_html_for_classification(html_content, aggressive_cleaning=True):
    """
    Limpeza específica para classificação de portais
    Foco em manter apenas elementos que ajudam a identificar tipo de portal
    """
    cleaning_options = {
        "preserve_structure": True,
        "max_length": 4000,  # Limite mais agressivo
        "remove_classes": aggressive_cleaning,
        "keep_semantic_attrs": aggressive_cleaning,
    }

    result = clean_html_for_llm(html_content, **cleaning_options)

    if aggressive_cleaning:
        # Segunda passada: limpeza ultra-minimal
        result["ultra_minimal_html"] = clean_html_ultra_minimal(result["cleaned_html"])
        result["structure_only_html"] = clean_html_structure_only(html_content)
        result["ultra_minimal_size"] = len(result["ultra_minimal_html"])
        result["structure_only_size"] = len(result["structure_only_html"])

    return result


def clean_html_aggressive(html_content, target_elements=None):
    """
    Limpeza agressiva focando apenas em elementos específicos
    """
    if target_elements is None:
        target_elements = [
            "nav",
            "menu",
            "header",
            "main",
            "section",
            "form",
            "table",
            "a",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
        ]

    soup = BeautifulSoup(html_content, "html.parser")

    # Manter apenas elementos alvo e seus textos
    relevant_content = []

    for element_type in target_elements:
        elements = soup.find_all(element_type)
        for element in elements:
            # Extrair informações relevantes
            element_info = {
                "tag": element.name,
                "text": element.get_text(strip=True),
                "href": element.get("href", "") if element.name == "a" else "",
                "children_count": len(element.find_all()),
            }

            if element_info["text"]:  # Só adicionar se tem conteúdo
                relevant_content.append(element_info)

    return relevant_content


def compare_cleaning_methods(html_content):
    """
    Compara diferentes métodos de limpeza para escolher o melhor
    """
    original_size = len(html_content)

    methods = {
        "padrao": clean_html_for_llm(html_content, remove_classes=False),
        "sem_classes": clean_html_for_llm(html_content, remove_classes=True),
        "semantico_puro": clean_html_for_llm(
            html_content, remove_classes=True, keep_semantic_attrs=True
        ),
        "ultra_minimal": {"cleaned_html": clean_html_ultra_minimal(html_content)},
        "estrutura_apenas": {"cleaned_html": clean_html_structure_only(html_content)},
    }

    # Calcular estatísticas para todos os métodos
    for method_name, result in methods.items():
        if "cleaned_size" not in result:
            result["cleaned_size"] = len(result["cleaned_html"])
            result["compression_ratio"] = (
                (original_size - result["cleaned_size"]) / original_size * 100
            )

    # Criar relatório comparativo
    comparison = {"original_size": original_size, "methods": {}}

    for method_name, result in methods.items():
        comparison["methods"][method_name] = {
            "size": result["cleaned_size"],
            "compression": result["compression_ratio"],
            "content_preview": (
                result["cleaned_html"][:200] + "..."
                if len(result["cleaned_html"]) > 200
                else result["cleaned_html"]
            ),
        }

    return comparison
