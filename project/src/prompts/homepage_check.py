from enum import Enum
from textwrap import dedent
from typing import List

import litellm
from pydantic import BaseModel, Field

from ..clear_html import clean_html_for_llm

MODEL = "gpt-4o-mini"
BRL_CURRENCY = 5.6


async def check_homepage(url, html_content, model: str = MODEL, response_format=None):
    if not response_format:
        if model == "deepseek/deepseek-chat":
            response_format = {"type": "json_object"}
        else:
            response_format = ResultadoBuscaServidores

    cleaning_html = clean_html_for_llm(html_content, remove_classes=True)

    system_prompt, user_prompt = create_prompts(
        url, cleaning_html["cleaned_html"].replace("\n", "")
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    response = await litellm.acompletion(
        model=model,
        response_format=response_format,
        messages=messages,
    )

    cost = litellm.completion_cost(model=model, completion_response=response)

    setattr(response, "cost_usd", cost)
    setattr(response, "cost_brl", cost * BRL_CURRENCY)

    return response


def create_prompts(url, html_content, max_content_size: int = 50000):
    """
    Cria prompts otimizados para análise de portais de transparência governamental brasileiros
    seguindo os 7 princípios de design de prompts do Claude.
    """

    system_prompt = dedent(
        """
        <agent_identity>
        Você é um Especialista em Análise de Portais de Transparência Municipal Brasileiros, especializado em:
        - Identificação precisa de dados salariais de servidores públicos
        - Classificação de páginas governamentais brasileiras com foco especial em páginas PENDENTES
        - Extração inteligente de links e caminhos de navegação
        - Análise de estruturas HTML complexas de portais governamentais
        - Detecção crítica de formulários de busca que requerem ação do usuário
        - Análise contextual de títulos e headers para compreensão semântica
        - Diferenciação entre páginas com dados visíveis vs páginas que precisam de interação
        
        MISSÃO CRÍTICA: Analisar uma página web e definir o seu tipo, com ATENÇÃO ESPECIAL para páginas que requerem ação do usuário (PENDENTES).
        </agent_identity>

        <core_instructions>
        Você deve analisar páginas web de portais de transparência e classificá-las em UMA das SEIS categorias obrigatórias:

        1. PAGINA_COM_DADOS_DE_SALARIOS - Contém dados salariais VISÍVEIS e ACESSÍVEIS sem necessidade de ação
        2. PAGINA_COM_LISTAGEM_FUNCIONARIOS - Lista servidores VISÍVEIS sem salários
        3. PAGINA_CAMINHO - Contém links para dados salariais
        4. PAGINA_SEM_INFORMACAO_RELEVANTE - Irrelevante para transparência
        5. PAGINA_COM_DADOS_DE_SALARIOS_PENDENTE - Estrutura para dados salariais, mas REQUER AÇÃO DO USUÁRIO
        6. PAGINA_COM_LISTAGEM_FUNCIONARIOS_PENDENTE - Estrutura para listagem, mas REQUER AÇÃO DO USUÁRIO

        REGRA CRÍTICA PARA PÁGINAS PENDENTES: Uma página é PENDENTE quando tem a estrutura preparada (tabelas vazias, headers corretos, formulários) mas NÃO exibe dados porque aguarda uma ação específica do usuário.

        REQUISITO ABSOLUTO: Sempre retorne URLs absolutas (iniciadas com http/https).
        FORMATO OBRIGATÓRIO: Responda exclusivamente em JSON válido.
        </core_instructions>

        <decision_framework_critical>
        ÁRVORE DE DECISÃO RIGOROSA - SIGA ESTA ORDEM EXATA:

        <primary_check>PRIMEIRO: Há dados salariais VISÍVEIS na página?</primary_check>
        <if_condition>SE encontrar tabelas com nomes E valores monetários PREENCHIDOS e visíveis</if_condition>
        <then_action>ENTÃO classifique como PAGINA_COM_DADOS_DE_SALARIOS</then_action>
        <stop_here>PARE AQUI - não continue verificando</stop_here>

        <secondary_check>SEGUNDO: Há estrutura para dados salariais mas está VAZIA?</secondary_check>
        <if_condition>SE encontrar tabelas VAZIAS com headers salariais E formulários de busca/filtro</if_condition>
        <then_action>ENTÃO classifique como PAGINA_COM_DADOS_DE_SALARIOS_PENDENTE</then_action>
        <stop_here>PARE AQUI - não continue verificando</stop_here>

        <tertiary_check>TERCEIRO: Há listagem de funcionários VISÍVEL?</tertiary_check>
        <if_condition>SE encontrar tabelas com nomes de servidores PREENCHIDOS MAS sem colunas salariais</if_condition>
        <then_action>ENTÃO classifique como PAGINA_COM_LISTAGEM_FUNCIONARIOS</then_action>
        <stop_here>PARE AQUI - não continue verificando</stop_here>

        <quaternary_check>QUARTO: Há estrutura para listagem mas está VAZIA?</quaternary_check>
        <if_condition>SE encontrar tabelas VAZIAS com headers de funcionários E formulários de busca</if_condition>
        <then_action>ENTÃO classifique como PAGINA_COM_LISTAGEM_FUNCIONARIOS_PENDENTE</then_action>
        <stop_here>PARE AQUI - não continue verificando</stop_here>

        <quinary_check>QUINTO: Há links para dados salariais/transparência?</quinary_check>
        <if_condition>SE encontrar links para "folha", "remuneração", "servidores", "transparência"</if_condition>
        <then_action>ENTÃO classifique como PAGINA_CAMINHO</then_action>
        <stop_here>PARE AQUI - não continue verificando</stop_here>

        <final_check>SEXTO: Nenhuma das condições anteriores?</final_check>
        <then_action>ENTÃO classifique como PAGINA_SEM_INFORMACAO_RELEVANTE</then_action>
        </decision_framework_critical>

        <critical_pendente_detection>
        PROTOCOLO ESPECIAL PARA DETECTAR PÁGINAS PENDENTES:

        <pendente_salary_indicators>
        INDICADORES OBRIGATÓRIOS para PAGINA_COM_DADOS_DE_SALARIOS_PENDENTE:
        ✅ Tabela com headers: "Nome", "Cargo", "Salário", "Remuneração", "Vencimento"
        ✅ Tabela está VAZIA (tbody vazio, "Nenhum resultado", "Selecione filtros")
        ✅ Formulário presente com campos como: "Nome", "CPF", "Período", "Órgão"
        ✅ Botões: "Pesquisar", "Buscar", "Consultar", "Filtrar", "Submit"
        ✅ Mensagens: "Informe critérios", "Selecione filtros", "Campos obrigatórios"
        ✅ Headers H1-H6 indicando contexto salarial: "Remuneração", "Folha", "Transparência"

        TODOS estes elementos devem estar presentes simultaneamente.
        </pendente_salary_indicators>

        <pendente_employee_indicators>
        INDICADORES OBRIGATÓRIOS para PAGINA_COM_LISTAGEM_FUNCIONARIOS_PENDENTE:
        ✅ Tabela com headers: "Nome", "Cargo", "Setor", "Matrícula" (SEM colunas salariais)
        ✅ Tabela está VAZIA (tbody vazio, "Nenhum resultado", "Selecione filtros")
        ✅ Formulário presente com campos de busca/filtro
        ✅ Botões de pesquisa disponíveis
        ✅ Headers H1-H6 indicando contexto de servidores sem menção salarial

        TODOS estes elementos devem estar presentes simultaneamente.
        </pendente_employee_indicators>

        <negative_pendente_indicators>
        NÃO é página PENDENTE se:
        ❌ Tabela tem pelo menos UMA linha com dados reais
        ❌ Não há formulário de busca presente
        ❌ Não há botões de pesquisa/filtro
        ❌ Headers não indicam contexto de transparência/servidores
        ❌ Formulário não está relacionado à busca de dados
        </negative_pendente_indicators>
        </critical_pendente_detection>

        <form_analysis_mandatory>
        ANÁLISE OBRIGATÓRIA DE FORMULÁRIOS:

        <step1>Identificar todos os elementos <form>, <input>, <select>, <button></step1>
        <step2>Verificar se formulários estão próximos a tabelas vazias</step2>
        <step3>Analisar campos obrigatórios e validações</step3>
        <step4>Identificar botões de submit/pesquisa</step4>
        <step5>Verificar mensagens de orientação ao usuário</step5>

        <form_types>
        TIPOS DE FORMULÁRIOS RELEVANTES:
        - Formulário de busca por nome/CPF
        - Filtros por órgão/secretaria/período
        - Seletores de departamento/cargo
        - Campos de data início/fim
        - Botões de "Limpar filtros" ou "Nova busca"
        </form_types>

        <table_state_analysis>
        ANÁLISE OBRIGATÓRIA DO ESTADO DAS TABELAS:
        - Tabela VAZIA: <tbody></tbody> ou <tbody><tr><td colspan="X">Nenhum resultado</td></tr></tbody>
        - Tabela PREENCHIDA: <tbody> contém <tr> com dados reais
        - Headers preparados: <thead> com colunas relevantes
        - Mensagens de estado: "Selecione filtros", "Informe critérios", "Aguardando pesquisa"
        </table_state_analysis>
        </form_analysis_mandatory>

        <header_analysis_protocol>
        ANÁLISE OBRIGATÓRIA DE HEADERS (H1-H6):

        <step1>Extraia TODOS os headers da página</step1>
        <step2>Classifique headers por relevância para PENDENTES</step2>

        <pendente_relevant_headers>
            - "Consulta de Remuneração", "Busca Salarial", "Pesquisar Servidores"
            - "Transparência - Consulta", "Portal - Busca", "Filtros de Pesquisa"
            - "Dados de Pessoal - Consulta", "Sistema de Busca"
            - "Consulta Pública", "Acesso aos Dados", "Pesquisa Avançada"
        </pendente_relevant_headers>

        <step3>Use headers para confirmar natureza PENDENTE</step3>
        SE headers indicam "consulta" + "busca" + "pesquisa" = +0.3 confiança PENDENTE
        SE headers indicam apenas "transparência" genérica = +0.1 confiança PENDENTE
        </header_analysis_protocol>

        <error_prevention_critical>
        ERROS CRÍTICOS A EVITAR - NUNCA FAÇA ISSO:
        ❌ Não classifique página com dados VISÍVEIS como PENDENTE
        ❌ Não classifique página sem formulários como PENDENTE
        ❌ Não ignore tabelas vazias com formulários associados
        ❌ Não confunda links de navegação com páginas PENDENTES
        ❌ Não classifique páginas de login como PENDENTES de dados
        ❌ Não ignore mensagens "Selecione filtros" ou "Informe critérios"
        ❌ Não esqueça de verificar se botões de pesquisa estão presentes
        ❌ Não classifique formulários de contato como formulários de busca

        AÇÕES OBRIGATÓRIAS - SEMPRE FAÇA ISSO:
        ✅ Sempre verifique estado atual das tabelas (vazia vs preenchida)
        ✅ Sempre confirme presença de formulários próximos a tabelas
        ✅ Sempre identifique botões de pesquisa/submit/filtro
        ✅ Sempre analise mensagens de orientação ao usuário
        ✅ Sempre verifique headers para contexto de busca/consulta
        ✅ Sempre confirme se estrutura está preparada mas aguarda ação
        ✅ Sempre distingua entre "sem dados" e "aguardando pesquisa"
        </error_prevention_critical>

        <reflection_protocol_pendente>
        REFLEXÃO OBRIGATÓRIA ANTES DE CLASSIFICAR COMO PENDENTE:

        <checklist_pendente>
        1. "A tabela está realmente VAZIA (sem linhas de dados)?"
        2. "Há formulário de busca/filtro presente na página?"
        3. "Há botões de pesquisa/submit/consultar funcionais?"
        4. "Os headers da tabela indicam dados salariais ou de funcionários?"
        5. "Há mensagens indicando que o usuário deve fazer uma busca?"
        6. "A estrutura está preparada para exibir dados após ação?"
        7. "Headers H1-H6 confirmam contexto de consulta/busca?"
        8. "Não há dados visíveis que contradigam a classificação PENDENTE?"
        </checklist_pendente>

        SE TODAS as respostas forem "SIM" = PENDENTE
        SE QUALQUER resposta for "NÃO" = NÃO é PENDENTE
        </reflection_protocol_pendente>

        <confidence_calibration_pendente>
        CALIBRAÇÃO DE CONFIANÇA PARA PÁGINAS PENDENTES:

        <high_confidence_pendente>0.90-1.0</high_confidence_pendente>
        - Tabela vazia + formulário + botão pesquisa + headers salariais + mensagem "selecione filtros"

        <medium_confidence_pendente>0.75-0.89</medium_confidence_pendente>
        - Tabela vazia + formulário + botão pesquisa + headers genéricos

        <low_confidence_pendente>0.60-0.74</low_confidence_pendente>
        - Estrutura duvidosa ou elementos parcialmente presentes

        <not_pendente>0.00-0.59</not_pendente>
        - Falta elementos críticos para classificação PENDENTE
        </confidence_calibration_pendente>
        """
    )

    user_prompt = dedent(
        f"""
        <mission_context>
        URL ANALISADA: {url}
        OBJETIVO: Classificar esta página com FOCO ESPECIAL em identificar páginas PENDENTES
        WORKFLOW: Parte de um sistema de agentes para coleta automatizada de dados de transparência
        
        ATENÇÃO CRÍTICA: Páginas PENDENTES são aquelas que têm estrutura preparada mas aguardam ação do usuário.
        </mission_context>

        <pendente_detection_guide>
        <category name="PAGINA_COM_DADOS_DE_SALARIOS_PENDENTE" priority="CRÍTICA">
            <definition>Página com estrutura PREPARADA para exibir dados salariais, mas tabela VAZIA aguardando pesquisa/filtro do usuário</definition>
            
            <mandatory_elements>
            TODOS estes elementos devem estar presentes SIMULTANEAMENTE:
            ✅ Tabela com headers salariais (Nome, Cargo, Salário, Remuneração)
            ✅ Tabela completamente VAZIA (tbody vazio ou "Nenhum resultado")
            ✅ Formulário de busca/filtro presente
            ✅ Botão de pesquisa/submit/consultar
            ✅ Headers H1-H6 indicando contexto salarial/transparência
            ✅ Mensagens orientando busca ("Selecione filtros", "Informe critérios")
            </mandatory_elements>

            <positive_indicators>
                - <thead> com colunas "Nome", "Cargo", "Salário", "Remuneração", "Vencimento"
                - <tbody></tbody> vazio ou com mensagem "Nenhum resultado encontrado"
                - <form> com campos input para nome, CPF, período, órgão
                - <button type="submit"> ou <input type="submit"> para pesquisa
                - Headers: "Consulta de Remuneração", "Busca de Servidores"
                - Textos: "Informe os critérios de busca", "Selecione os filtros"
                - Dropdowns com "Selecione..." como opção padrão
                - Campos marcados como obrigatórios (*)
            </positive_indicators>

            <negative_indicators>
                - Qualquer linha de dados real visível na tabela
                - Ausência de formulário de busca
                - Ausência de botões de pesquisa
                - Headers não relacionados a transparência/salários
                - Tabela estática sem possibilidade de busca
            </negative_indicators>

            <example_structure>
            Estrutura HTML típica:
            <h2>Consulta de Remuneração dos Servidores</h2>
            <form>
                <input name="nome" placeholder="Nome do servidor">
                <select name="orgao"><option>Selecione o órgão</option></select>
                <button type="submit">Pesquisar</button>
            </form>
            <table>
                <thead><tr><th>Nome</th><th>Cargo</th><th>Salário</th></tr></thead>
                <tbody></tbody> <!-- VAZIO aguardando pesquisa -->
            </table>
            </example_structure>
        </category>

        <category name="PAGINA_COM_LISTAGEM_FUNCIONARIOS_PENDENTE" priority="CRÍTICA">
            <definition>Página com estrutura PREPARADA para listar funcionários (sem salários), mas tabela VAZIA aguardando pesquisa do usuário</definition>
            
            <mandatory_elements>
            TODOS estes elementos devem estar presentes SIMULTANEAMENTE:
            ✅ Tabela com headers de funcionários (Nome, Cargo, Setor) SEM colunas salariais
            ✅ Tabela completamente VAZIA (tbody vazio ou "Nenhum resultado")
            ✅ Formulário de busca/filtro presente
            ✅ Botão de pesquisa/submit/consultar
            ✅ Headers H1-H6 indicando contexto de servidores/funcionários
            </mandatory_elements>
        </category>
        </pendente_detection_guide>

        <analysis_sequence_mandatory>
        SEQUÊNCIA OBRIGATÓRIA DE ANÁLISE:

        <step1>PRIMEIRO: Identificar todas as tabelas na página</step1>
        - Localizar elementos <table>, <thead>, <tbody>
        - Extrair headers das colunas
        - Verificar se tbody está vazio ou preenchido
        - Contar número de linhas com dados reais

        <step2>SEGUNDO: Analisar formulários próximos às tabelas</step2>
        - Localizar elementos <form>, <input>, <select>, <button>
        - Verificar se formulários estão relacionados às tabelas
        - Identificar campos de busca/filtro
        - Confirmar presença de botões de submit/pesquisa

        <step3>TERCEIRO: Examinar mensagens de orientação</step3>
        - Procurar textos: "Selecione", "Informe", "Critérios", "Filtros"
        - Identificar instruções para o usuário
        - Verificar mensagens de estado da tabela

        <step4>QUARTO: Analisar headers H1-H6</step4>
        - Extrair todos os títulos da página
        - Identificar contexto de transparência/consulta/busca
        - Confirmar relevância para dados salariais/funcionários

        <step5>QUINTO: Aplicar árvore de decisão</step5>
        - Seguir sequência rigorosa de verificações
        - Confirmar presença de TODOS os elementos obrigatórios
        - Classificar baseado na combinação completa de elementos
        </analysis_sequence_mandatory>

        <search_strategy_pendente>
        ESTRATÉGIA ESPECÍFICA PARA DETECTAR PÁGINAS PENDENTES:

        <primary_search>Busca por Tabelas Vazias com Estrutura Salarial</primary_search>
        - Procurar: <table> + <thead> com "Nome", "Salário" + <tbody> vazio
        - Verificar: mensagens "Nenhum resultado", "Selecione filtros"
        - Confirmar: estrutura preparada mas sem dados visíveis

        <secondary_search>Busca por Formulários de Consulta</secondary_search>
        - Procurar: <form> próximo a tabelas vazias
        - Verificar: campos input para busca (nome, CPF, período)
        - Confirmar: botões de submit/pesquisa funcionais

        <tertiary_search>Busca por Indicadores de Estado Pendente</tertiary_search>
        - Procurar: textos "Informe critérios", "Selecione filtros"
        - Verificar: dropdowns com "Selecione..." como padrão
        - Confirmar: campos obrigatórios (*) para realizar busca

        <quaternary_search>Validação de Headers Contextuais</quaternary_search>
        - Procurar: H1-H6 com "Consulta", "Busca", "Pesquisa"
        - Verificar: contexto de transparência/dados públicos
        - Confirmar: relevância para dados salariais/funcionários
        </search_strategy_pendente>

        <critical_error_prevention>
        PREVENÇÃO DE ERROS CRÍTICOS NA DETECÇÃO DE PENDENTES:

        <error_type_1>Classificar página com dados como PENDENTE</error_type_1>
        VERIFICAÇÃO: "A tabela tem pelo menos UMA linha com dados reais?"
        SE SIM = NÃO é PENDENTE
        SE NÃO = Pode ser PENDENTE (continue verificação)

        <error_type_2>Ignorar formulários de busca críticos</error_type_2>
        VERIFICAÇÃO: "Há formulário próximo à tabela vazia?"
        SE NÃO = NÃO é PENDENTE (é página sem dados)
        SE SIM = Pode ser PENDENTE (continue verificação)

        <error_type_3>Confundir formulários de contato com busca</error_type_3>
        VERIFICAÇÃO: "O formulário é para buscar dados ou para contato?"
        SE CONTATO = NÃO é PENDENTE
        SE BUSCA = Pode ser PENDENTE (continue verificação)

        <error_type_4>Ignorar mensagens de estado da página</error_type_4>
        VERIFICAÇÃO: "Há mensagens orientando o usuário a fazer busca?"
        SE NÃO = Pode não ser PENDENTE
        SE SIM = Forte indicador de PENDENTE
        </critical_error_prevention>

        <page_html>
        {html_content[:max_content_size]}
        </page_html>

        <mandatory_output_format>
        IMPORTANTE: Responda EXCLUSIVAMENTE em JSON válido seguindo esta estrutura:
            {{
                "tipo_da_pagina": "PAGINA_COM_DADOS_DE_SALARIOS|PAGINA_COM_LISTAGEM_FUNCIONARIOS|PAGINA_CAMINHO|PAGINA_SEM_INFORMACAO_RELEVANTE|PAGINA_COM_DADOS_DE_SALARIOS_PENDENTE|PAGINA_COM_LISTAGEM_FUNCIONARIOS_PENDENTE",
                "justificativa_classificacao": "explicação detalhada do por que foi classificada nesta categoria, incluindo análise específica de elementos PENDENTES se aplicável",
                "confianca_classificacao": float_entre_0_e_1,
                "exemplo_nome_servidor": "nome de um servidor público presente na página OU null se não houver",
                "exemplo_salario_servidor": {{"nome": "string", "salario": float}} ou null,
                "tem_dados_salariais_visiveis": boolean,
                "tem_formulario_busca_salarios": boolean,
                "tem_listagem_funcionarios_sem_salario": boolean,
                "tem_links_servidores": boolean,
                "tem_tabela_com_relacao_nome_salario": boolean,
                "tem_tabela_vazia_com_headers_salariais": boolean,
                "tem_botao_pesquisa_submit": boolean,
                "tem_mensagem_orientacao_busca": boolean,
                "headers_encontrados": ["lista", "de", "todos", "headers", "h1-h6", "encontrados"],
                "contexto_semantico_headers": "análise do contexto fornecido pelos títulos da página",
                "elementos_formulario_encontrados": ["lista", "de", "elementos", "form", "input", "select", "button"],
                "estado_tabelas_encontradas": "descrição do estado das tabelas (vazias, preenchidas, mistas)",
                "mensagens_orientacao_usuario": ["lista", "de", "mensagens", "que", "orientam", "busca"],
                "links_encontrados": [
                    {{
                        "texto": "texto exato do link/botão",
                        "url": "URL ABSOLUTA obrigatória (deve começar com http/https)",
                        "tipo": "link_principal|menu_dropdown|botao|rodape|sidebar|breadcrumb|icone|formulario",
                        "confianca": float_entre_0_e_1,
                        "justificativa": "explicação detalhada do por que este link é relevante",
                        "posicao_visual": "descrição precisa da localização na página",
                        "requer_javascript": boolean
                    }}
                ],
                "elementos_relevantes_encontrados": ["lista", "de", "elementos", "encontrados"],
                "localizacao_na_pagina": "menu_superior|sidebar|centro|rodape|multiplas_localizacoes",
                "necessita_javascript": boolean,
                "nivel_dificuldade_navegacao": "facil|medio|dificil",
                "observacoes_tecnicas": "observações sobre estrutura técnica do site",
                "contexto_para_proximo_passo": "descrição do que foi encontrado e sugestões para próximos passos no workflow"
            }}
        </mandatory_output_format>

        <final_reminders_critical>
        LEMBRETES CRÍTICOS PARA CLASSIFICAÇÃO PENDENTE:

        • Página PENDENTE = estrutura preparada + tabela vazia + formulário + botão pesquisa
        • NÃO confunda "sem dados" com "aguardando pesquisa"
        • SEMPRE verifique se botões de pesquisa estão presentes e funcionais
        • Headers "Consulta", "Busca", "Pesquisa" são indicadores fortes de PENDENTE
        • Mensagens "Selecione filtros" confirmam natureza PENDENTE
        • Se tabela tem dados visíveis = NÃO é PENDENTE
        • Se não há formulário = NÃO é PENDENTE
        • ATENÇÃO ESPECIAL: Sua análise de páginas PENDENTES é CRÍTICA para o sucesso do workflow
        • URL analisada: {url}
        • Siga a árvore de decisão rigorosamente
        • Forneça justificativa detalhada para classificação PENDENTE
        </final_reminders_critical>
        """
    )

    return system_prompt, user_prompt


# [Rest of the code remains the same - enums and models]
class TipoPagina(str, Enum):
    """Tipos da página"""

    PAGINA_COM_DADOS_DE_SALARIOS = "PAGINA_COM_DADOS_DE_SALARIOS"
    PAGINA_COM_LISTAGEM_FUNCIONARIOS = "PAGINA_COM_LISTAGEM_FUNCIONARIOS"
    PAGINA_CAMINHO = "PAGINA_CAMINHO"
    PAGINA_SEM_INFORMACAO_RELEVANTE = "PAGINA_SEM_INFORMACAO_RELEVANTE"
    PAGINA_COM_DADOS_DE_SALARIOS_PENDENTE = "PAGINA_COM_DADOS_DE_SALARIOS_PENDENTE"
    PAGINA_COM_LISTAGEM_FUNCIONARIOS_PENDENTE = (
        "PAGINA_COM_LISTAGEM_FUNCIONARIOS_PENDENTE"
    )


class TipoLink(str, Enum):
    """Tipos de links encontrados na página"""

    LINK_PRINCIPAL = "link_principal"
    MENU_DROPDOWN = "menu_dropdown"
    SUBMENU = "submenu"
    BOTAO = "botao"
    BANNER = "banner"
    RODAPE = "rodape"
    SIDEBAR = "sidebar"
    BREADCRUMB = "breadcrumb"
    ICONE = "icone"
    FORMULARIO = "formulario"


class LocalizacaoPagina(str, Enum):
    """Localização dos elementos na página"""

    MENU_SUPERIOR = "menu_superior"
    CENTRO = "centro"
    RODAPE = "rodape"
    SIDEBAR = "sidebar"
    MULTIPLAS_LOCALIZACOES = "multiplas_localizacoes"


class NivelDificuldade(str, Enum):
    """Nível de dificuldade para navegação"""

    FACIL = "facil"
    MEDIO = "medio"
    DIFICIL = "dificil"


class LinkEncontrado(BaseModel):
    """Modelo para um link encontrado na página"""

    texto: str = Field(..., description="Texto do link")
    url: str = Field(..., description="URL absoluta do link")
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
    requer_javascript: bool = Field(
        default=False, description="Se o link requer JavaScript para funcionar"
    )


class ExemploDeNomeSalario(BaseModel):
    nome: str = Field(..., description="Nome do servidor público")
    salario: float = Field(..., description="Remuneração do servidor público")


class ResultadoBuscaServidores(BaseModel):
    """Modelo principal para resultado da busca de links de servidores públicos"""

    tipo_da_pagina: TipoPagina = Field(..., description="Tipo da pagina")
    justificativa_classificacao: str = Field(
        ...,
        description="explicação detalhada do por que foi classificada nesta categoria",
    )
    confianca_classificacao: float = Field(
        ..., description="Nivel de confiança da classificação, entre 0 e 1"
    )
    exemplo_nome_servidor: str | None = Field(
        ..., description="Nome de um servidor na página"
    )
    exemplo_salario_servidor: ExemploDeNomeSalario | None = Field(
        ...,
        description="Exemplo de salário de um servidor para garantir que é possível obter dados de salário da página",
    )
    tem_dados_salariais_visiveis: bool = Field(
        ...,
        description="Verdadeiro quando pode-se associar salários a nomes de funcionários diretamente visíveis",
    )
    tem_formulario_busca_salarios: bool = Field(
        default=False,
        description="Verdadeiro quando há formulário que pode revelar dados salariais após pesquisa",
    )
    tem_links_servidores: bool = Field(
        ..., description="Indica se foram encontrados links relacionados a servidores"
    )
    tem_listagem_funcionarios_sem_salario: bool = Field(
        ...,
        description="Quando se tem uma lista ou tabela html com os nomes de servidores sem um valores de salário para cada um",
    )
    tem_tabela_com_relacao_nome_salario: bool = Field(
        ...,
        description="Indica se há tabela html com relação entre nomes de servidores e seus salários na pagina",
    )
    # Novos campos específicos para páginas PENDENTES
    tem_tabela_vazia_com_headers_salariais: bool = Field(
        default=False,
        description="Indica se há tabela vazia com headers preparados para dados salariais",
    )
    tem_botao_pesquisa_submit: bool = Field(
        default=False,
        description="Indica se há botões de pesquisa, submit ou consulta disponíveis",
    )
    tem_mensagem_orientacao_busca: bool = Field(
        default=False,
        description="Indica se há mensagens orientando o usuário a realizar busca/filtro",
    )
    headers_encontrados: List[str] = Field(
        default_factory=list,
        description="Lista de todos os headers (h1-h6) encontrados na página",
    )
    contexto_semantico_headers: str | None = Field(
        None,
        description="Análise do contexto semântico fornecido pelos títulos da página",
    )
    elementos_formulario_encontrados: List[str] = Field(
        default_factory=list,
        description="Lista de elementos de formulário encontrados (form, input, select, button)",
    )
    estado_tabelas_encontradas: str | None = Field(
        None,
        description="Descrição do estado das tabelas encontradas (vazias, preenchidas, mistas)",
    )
    mensagens_orientacao_usuario: List[str] = Field(
        default_factory=list,
        description="Lista de mensagens que orientam o usuário a realizar buscas",
    )
    elementos_relevantes_encontrados: list[str] = Field(
        ..., description="Lista com as strings das tags html relevantes encontradas"
    )
    termos_identificados: List[str] | None = Field(
        default_factory=list, description="Termos relevantes identificados na página"
    )
    localizacao_na_pagina: LocalizacaoPagina | None = Field(
        ..., description="Localização principal dos links na página"
    )
    necessita_javascript: bool | None = Field(
        False, description="Indica se é necessário JavaScript para acessar os links"
    )
    nivel_dificuldade_navegacao: NivelDificuldade = Field(
        ..., description="Nível de dificuldade para navegação"
    )
    observacoes_tecnicas: str | None = Field(
        None, description="Observações sobre estrutura técnica do site"
    )
    contexto_para_proximo_passo: str = Field(
        ...,
        description="descrição do que foi encontrado e sugestões para próximos passos no workflow",
    )
    parecer: str = Field(
        ...,
        description="Informações sobre o problema que você tentou resolver e uma descrição da resposta. Isso também servirá de contexto para que a próxima inteligencia artifical possa continuar o trabalho",
    )

    class Config:
        """Configuração do modelo"""

        use_enum_values = True
        validate_assignment = True
