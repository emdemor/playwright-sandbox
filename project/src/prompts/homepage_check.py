from textwrap import dedent

from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum

import litellm

from ..clear_html import clean_html_for_llm

MODEL = "gpt-4o-mini"
BRL_CURRENCY = 5.6


async def check_homepage(url, html_content):

    cleaning_html = clean_html_for_llm(html_content, remove_classes=True)

    system_prompt, user_prompt = create_prompts(
        url, cleaning_html["cleaned_html"].replace("\n", "")
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    response = await litellm.acompletion(
        model=MODEL,
        response_format=ResultadoBuscaServidores,
        messages=messages,
    )

    cost = litellm.completion_cost(model=MODEL, completion_response=response)

    setattr(response, "cost_usd", cost)
    setattr(response, "cost_brl", cost * BRL_CURRENCY)

    return response


def create_prompts(url, html_content, max_content_size: int = 50000):
    """
    Cria o prompt para P1: Identificação de Links Relevantes
    """

    system_prompt = dedent(
        """
    Você é um especialista em análise de portais de transparência governamental brasileiros. 
    Sua missão é ajudar a construir um agente de IA para coletar dados salariais de servidores públicos municipais.

    INSTRUÇÕES IMPORTANTES:
    1. Analise CUIDADOSAMENTE tanto a captura de tela quanto o código HTML fornecido
    2. Procure por links, botões ou menus que possam levar a informações sobre:
       - Transparência
       - Servidores públicos
       - Folha de pagamento
       - Salários e remuneração
       - Recursos humanos
       - Portal da transparência
       - Gastos públicos
       - Despesas com pessoal

    3. Considere variações regionais nos termos (ex: "funcionários", "colaboradores", "quadro de pessoal")
    4. Observe tanto elementos visuais óbvios quanto links menos evidentes no rodapé ou menus secundários
    5. Avalie a confiança baseada na clareza e relevância do link encontrado

    RESPONDA SEMPRE EM JSON VÁLIDO seguindo EXATAMENTE a estrutura especificada."""
    )

    user_prompt = dedent(
        f"""

    <main-question>
    Na página atual, existem links ou botões que levam para informações sobre servidores públicos, transparência, folha de pagamento ou salários?
    </main-question>

    URL ANALISADA: {url}

    CONTEXTO ADICIONAL:
    <context>
    - Esta é a homepage de um portal municipal brasileiro
    - Estamos buscando o caminho para acessar dados de remuneração de servidores públicos
    - Links podem estar em menus principais, rodapé, ou seções específicas de transparência
    </context>

    ANÁLISE REQUERIDA:
    <required-analysis>
    1. Examine a captura de tela para identificar elementos visuais relevantes
    2. Analise o HTML para encontrar links e estruturas de navegação
    3. Identifique termos-chave relacionados à transparência e servidores públicos
    4. Determine a localização e tipo de cada link encontrado
    5. Se o link encontrado for relativo, utilize a url da página para compor o link global
    </required-analysis>

    RESPONDA EM JSON SEGUINDO ESTA ESTRUTURA EXATA:
    <output-format>
    {{
      "tem_links_servidores": boolean,
      "tem_tabela_com_relacao_nome_salario": boolean,
      "links_encontrados": [
        {{
          "texto": "texto exato do link/botão",
          "url": "URL relativa ou absoluta",
          "tipo": "link_principal|menu_dropdown|botao|rodape|sidebar|breadcrumb",
          "confianca": float_entre_0_e_1,
          "justificativa": "breve explicação do por que este link é relevante",
          "posicao_visual": "descrição da localização na página"
        }}
      ],
      "termos_identificados": ["lista", "de", "termos", "relevantes", "encontrados"],
      "localizacao_na_pagina": "menu_superior|sidebar|centro|rodape|multiplas_localizacoes",
      "observacoes_adicionais": "qualquer observação importante sobre a estrutura do site",
      "necessita_javascript": boolean,
      "nivel_dificuldade_navegacao": "facil|medio|dificil"
    }}
    </output-format>

    CÓDIGO HTML DA PÁGINA:
    <page-html>
    {html_content[:max_content_size]}
    </page-html>

    <additional-important-information>
    IMPORTANTE: Se não encontrar links óbvios, procure por:
    - Menus que possam ter submenus
    - Links no rodapé
    - Seções como "Acesso à Informação" ou "LAI"
    - Ícones sem texto descritivo
    - Links em outras linguagens ou abreviações

    IMPORTANTE: os links relevantes deve começar com `http`. Links relativos não podem ser utilizados.
    </additional-important-information>
    """
    )

    return system_prompt, user_prompt


class TipoLink(str, Enum):
    """Tipos de links encontrados na página"""

    LINK_PRINCIPAL = "link_principal"
    MENU_DROPDOWN = "menu_dropdown"
    SUBMENU = "submenu"
    BOTAO = "botao"
    BANNER = "banner"


class LocalizacaoPagina(str, Enum):
    """Localização dos elementos na página"""

    TOPO = "topo"
    CENTRO = "centro"
    RODAPE = "rodape"
    LATERAL = "lateral"


class NivelDificuldade(str, Enum):
    """Nível de dificuldade para navegação"""

    FACIL = "facil"
    MEDIO = "medio"
    DIFICIL = "dificil"


class LinkEncontrado(BaseModel):
    """Modelo para um link encontrado na página"""

    texto: str = Field(..., description="Texto do link")
    url: str = Field(..., description="URL do link (pode ser relativa ou absoluta)")
    tipo: TipoLink = Field(..., description="Tipo do link encontrado")
    confianca: float = Field(
        ..., ge=0.0, le=1.0, description="Nível de confiança (0.0 a 1.0)"
    )
    justificativa: str = Field(
        ..., description="Justificativa para o nível de confiança"
    )
    posicao_visual: str = Field(
        ..., description="Descrição da posição visual do link na página"
    )


class ResultadoBuscaServidores(BaseModel):
    """Modelo principal para resultado da busca de links de servidores públicos"""

    tem_links_servidores: bool = Field(
        ..., description="Indica se foram encontrados links relacionados a servidores"
    )
    tem_tabela_com_relacao_nome_salario: bool = Field(
        ...,
        description="Indica se há relação entre nomes de servidores e seus salários",
    )
    links_encontrados: List[LinkEncontrado] = Field(
        default_factory=list, description="Lista de links encontrados"
    )
    termos_identificados: List[str] = Field(
        default_factory=list, description="Termos relevantes identificados na página"
    )
    localizacao_na_pagina: LocalizacaoPagina = Field(
        ..., description="Localização principal dos links na página"
    )
    observacoes_adicionais: Optional[str] = Field(
        None, description="Observações adicionais sobre a busca"
    )
    necessita_javascript: bool = Field(
        False, description="Indica se é necessário JavaScript para acessar os links"
    )
    nivel_dificuldade_navegacao: NivelDificuldade = Field(
        ..., description="Nível de dificuldade para navegação"
    )

    class Config:
        """Configuração do modelo"""

        use_enum_values = True
        validate_assignment = True
