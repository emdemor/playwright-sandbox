Aprimore o seguinte prompt:

```
def get_promtp():
    user_prompt = dedent(
        f"""
        <primary_mission>
        Você é um especialista em análise de portais de transparência municipal brasileiros.
        Você faz parte de um sistem de agentes de inteligencia artifiial cujo objetivo é fazer
        o download de dados de salário de servidores públicos municipais do Brasil.

        Você receberá a URL e o CÓDIGO HTML de uma página web de uma portal de transparência.
        Sua tarefa é identificar se essa página se encaixa em alguma dessas categorias:

        1. PAGINA COM DADOS DE SALARIOS
        2. PAGINA CAMINHO
        3. PAGINA SEM INFORMACAO RELEVANTE

        <page_types_context>
            - **PAGINA COM DADOS DE SALARIOS**: é uma página onde de fato, temos a listagem dos servidores, com seus nomes e seus salários. Em alguns casos, pode ser que o salário não esteja explícito, mas pode ser acessado através de algum link ou meno dropdown.
            - **PAGINA CAMINHO**: é uma página onde não temos dados de salários para os servidores, mas ela tem no mínimo um link para uma **PAGINA COM DADOS DE SALARIOS** ou para uma outra **PAGINA CAMINHO**. Essas páginas são importante para a navegação até uma **PAGINA COM DADOS DE SALARIOS**.
            - **PAGINA SEM INFORMACAO RELEVANTE**: é uma página sem informações relevantes com respeito a relação nome e salário de servidores públicos
        </page_types_context>

        Sua missão é identificar o tipo da página e, caso seja uma **PAGINA CAMINHO**, identificar com precisão caminhos para acessar dados de remuneração de servidores públicos na página atual.

        URL ANALISADA: {url}
        </primary_mission>

        <main_question>
        Na página atual, existem links ou botões que levam para informações sobre servidores públicos, transparência, folha de pagamento ou salários?
        </main_question>

        <context_information>
        - Esta é a homepage de um portal municipal brasileiro
        - Estamos buscando especificamente o caminho para acessar dados de remuneração de servidores públicos
        - Links podem estar em menus principais, rodapé, seções específicas de transparência, ou mesmo como ícones sem texto descritivo
        - Portais municipais brasileiros frequentemente seguem padrões da Lei de Acesso à Informação (LAI)
        </context_information>

        <critical_analysis_requirements>
        1. Examine TODA a captura de tela para identificar elementos visuais relevantes
        2. Analise COMPLETAMENTE o HTML para encontrar links e estruturas de navegação
        3. Identifique termos-chave relacionados à transparência e servidores públicos
        4. Determine a localização precisa e tipo de cada link encontrado
        5. OBRIGATÓRIO: Se encontrar links relativos, converta-os para URLs absolutas usando a URL base: {url}
        6. No final, dê um parecer sobre o problema que você tentou resolver e uma descrição da resposta. Isso servirá de contexto para que a próxima inteligencia artifical possa continuar o trabalho.
        </critical_analysis_requirements>

        <search_strategy>
        SE não encontrar links óbvios sobre transparência, ENTÃO procure por:
        - Menus dropdown que possam conter submenus de transparência
        - Links no rodapé da página
        - Seções como "Acesso à Informação", "LAI", "Transparência", "Portal da Transparência"
        - Ícones ou imagens sem texto descritivo mas que possam representar transparência
        - Links em outras linguagens ou abreviações (ex: "CPLT", "SIC", "e-SIC")
        - Botões ou links com termos como "Servidores", "Pessoal", "Folha", "Remuneração"

        SE encontrar menus suspeitos, ENTÃO examine cuidadosamente se há submenu ou dropdown
        SE o site usar JavaScript para navegação, ENTÃO marque "necessita_javascript" como true
        </search_strategy>

        <error_prevention_rules>
        NUNCA retorne links relativos (que começam com "/", "./", "../") sem convertê-los para URLs absolutas
        NUNCA ignore links no rodapé ou em seções menos visíveis
        NUNCA assuma que um site não tem informações de transparência apenas porque não são óbvias
        NUNCA retorne confiança alta (>0.8) para links genéricos como "Serviços" sem análise contextual
        SEMPRE verifique se há JavaScript necessário para navegação
        SEMPRE analise o HTML completo, não apenas elementos visíveis
        </error_prevention_rules>

        <confidence_calibration>
        Confiança 0.9-1.0: Link explicitamente menciona "transparência", "servidores", "folha de pagamento", "remuneração"
        Confiança 0.7-0.8: Link está em seção de transparência ou usa termos relacionados como "LAI", "Acesso à Informação"
        Confiança 0.5-0.6: Link genérico em menu que pode conter informações de transparência
        Confiança 0.3-0.4: Link suspeito mas sem confirmação clara
        Confiança 0.1-0.2: Link muito genérico ou duvidoso
        </confidence_calibration>

        <mandatory_output_format>
        RESPONDA EXCLUSIVAMENTE EM JSON SEGUINDO ESTA ESTRUTURA EXATA:
        {{
        "tipo_da_página": "PAGINA_COM_DADOS_DE_SALARIOS|PAGINA_CAMINHO|PAGINA_SEM_INFORMACAO_RELEVANTE",
        "tem_links_servidores": boolean,
        "tem_tabela_com_relacao_nome_salario": boolean,
        "links_encontrados": [
            {{
            "texto": "texto exato do link/botão",
            "url": "URL ABSOLUTA obrigatória (deve começar com http/https)",
            "tipo": "link_principal|menu_dropdown|botao|rodape|sidebar|breadcrumb|icone",
            "confianca": float_entre_0_e_1,
            "justificativa": "explicação detalhada do por que este link é relevante",
            "posicao_visual": "descrição precisa da localização na página"
            }}
        ],
        "termos_identificados": ["lista", "de", "termos", "relevantes", "encontrados"],
        "localizacao_na_pagina": "menu_superior|sidebar|centro|rodape|multiplas_localizacoes",
        "observacoes_adicionais": "observações importantes sobre a estrutura do site",
        "necessita_javascript": boolean,
        "nivel_dificuldade_navegacao": "facil|medio|dificil"
        }}
        </mandatory_output_format>

        <quality_assurance_checklist>
        Antes de finalizar, verifique:
        ✓ Todos os links encontrados são URLs absolutas (começam com http/https)
        ✓ Analisou tanto elementos visíveis quanto código HTML
        ✓ Considerou menus dropdown e elementos JavaScript
        ✓ Avaliou corretamente o nível de confiança de cada link
        ✓ Incluiu observações sobre dificuldades de navegação
        ✓ Formato JSON está correto e completo
        </quality_assurance_checklist>

        <page_html>
        {html_content[:max_content_size]}
        </page_html>

        <final_reminder>
        LEMBRE-SE: Esta análise é crucial para acessar dados de transparência pública. Seja meticuloso na identificação de TODOS os possíveis caminhos, mesmo os menos óbvios. URLs devem ser SEMPRE absolutas.
        </final_reminder>
        """
    )

```

de acordo com os principios que regem os prompts do Claude, uma das IAs mais avançadas do mundo.

Os sete principios são:

1. Não tenha medo de escrever prompts grandes: O prompt do Claude tem cerca de 18.000 palavras, indicando que usar janelas de contexto maiores é eficaz para fornecer mais instruções e informações ao modelo.

2. Use XML para organizar blocos de instrução: A organização de prompts extensos com tags XML auxilia os modelos de linguagem a acessar informações de forma mais eficiente, como instruções específicas para pesquisas.

3. Um bom prompt é 80% prevenção e 20% instrução: Diferente de prompts amadores, o prompt do Claude foca em orientar o agente sobre o que não fazer e quais erros evitar, funcionando como uma política de tomada de decisão.

4. Programe a IA: use lógica condicional e regras binárias: O prompt do Claude emprega muitas condições "se... então... do contrário", programando a IA para reagir de diversas maneiras conforme a situação, como decidir quando realizar uma pesquisa na internet.

5. Melhore a eficiência do uso de ferramentas com exemplos negativos: Além de mostrar como usar uma ferramenta, o prompt também exemplifica como não usá-la, o que é valioso para o aprendizado da IA, similar ao aprendizado humano por análise de erros.

6. Incentive pausas para reflexões após chamadas de funções: Modelos de linguagem autorregressivos se beneficiam de "cadeias de pensamento" antes de gerar uma resposta, especialmente em áreas como ciência e matemática. O prompt do Claude instrui o modelo a pausar e refletir apenas quando necessário, otimizando o uso de tokens e melhorando o desempenho.

7. Repita instruções importantes ao longo do prompt: Para evitar que o modelo "esqueça" informações cruciais em prompts muito longos, o Claude repete estrategicamente dados importantes, como o nome da empresa ou do agente, aumentando a probabilidade de serem considerados na resposta.