FROM python:3.12.2-slim

# Adicionar argumentos para UID/GID do host
ARG UID=1000
ARG GID=1000

# Criar usuário e grupo com UID/GID do host
RUN groupadd -g $GID jovyan && \
    useradd -u $UID -g $GID -m jovyan

# Instalar dependências básicas incluindo sudo e ferramentas para terminal
RUN apt-get update && \
    apt-get install -y \
    pciutils wget cmake git build-essential libncurses5-dev libncursesw5-dev libsystemd-dev libudev-dev libdrm-dev pkg-config \
    sudo \
    bash \
    bash-completion \
    less \
    nano \
    vim \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Dar permissão sudo ao usuário jovyan sem senha
RUN echo "jovyan ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Install Jupyter
RUN pip install jupyter
RUN pip install ipywidgets
RUN pip install jupyter_contrib_nbextensions
RUN pip install jupyterlab_code_formatter black isort
RUN pip install JLDracula
RUN pip install jupyterlab_materialdarker
RUN pip install jupyterlab-drawio
RUN pip install jupyterlab_execute_time
RUN pip install ipympl
RUN pip install nbdime
RUN pip install jupyterlab-git
RUN pip install jupyter-resource-usage
RUN pip install jupyter-archive
RUN pip install jupyterlab-system-monitor
RUN pip install jupyterlab-cell-flash
RUN pip install lckr_jupyterlab_variableinspector
RUN pip install jupyterlab-unfold
RUN pip install jlab-enhanced-cell-toolbar
RUN pip install jupyterlab-spreadsheet-editor
RUN pip install jupyterlabcodetoc

# Instalar o Playwright
RUN pip install playwright

COPY ./requirements.txt .
RUN pip install -r requirements.txt

# Configurar diretórios com permissões corretas
RUN mkdir /project && \
    chown jovyan:jovyan /project && \
    chmod 755 /project

# Mudar para o usuário jovyan
USER jovyan

ENV PATH="/home/jovyan/.local/bin:${PATH}"
WORKDIR /home/jovyan
RUN mkdir /home/jovyan/.config

# Instalar browsers do Playwright e dependências com sudo
RUN playwright install
RUN sudo playwright install-deps

# Configurar o bash para o usuário jovyan
RUN echo 'export TERM=xterm-256color' >> /home/jovyan/.bashrc && \
    echo 'export SHELL=/bin/bash' >> /home/jovyan/.bashrc && \
    echo 'set -o vi' >> /home/jovyan/.bashrc && \
    echo 'bind "set completion-ignore-case on"' >> /home/jovyan/.bashrc && \
    echo 'bind "set show-all-if-ambiguous on"' >> /home/jovyan/.bashrc && \
    echo 'bind "set colored-stats on"' >> /home/jovyan/.bashrc && \
    echo 'bind "set colored-completion-prefix on"' >> /home/jovyan/.bashrc && \
    echo 'bind "set menu-complete-display-prefix on"' >> /home/jovyan/.bashrc && \
    echo 'shopt -s histappend' >> /home/jovyan/.bashrc && \
    echo 'export HISTCONTROL=ignoredups:erasedups' >> /home/jovyan/.bashrc && \
    echo 'export HISTSIZE=10000' >> /home/jovyan/.bashrc && \
    echo 'export HISTFILESIZE=10000' >> /home/jovyan/.bashrc

# Configurar inputrc para melhorar a experiência do terminal
RUN echo 'set editing-mode emacs' > /home/jovyan/.inputrc && \
    echo 'set completion-ignore-case on' >> /home/jovyan/.inputrc && \
    echo 'set show-all-if-ambiguous on' >> /home/jovyan/.inputrc && \
    echo 'set colored-stats on' >> /home/jovyan/.inputrc && \
    echo 'set colored-completion-prefix on' >> /home/jovyan/.inputrc && \
    echo 'set menu-complete-display-prefix on' >> /home/jovyan/.inputrc && \
    echo '"\e[A": history-search-backward' >> /home/jovyan/.inputrc && \
    echo '"\e[B": history-search-forward' >> /home/jovyan/.inputrc && \
    echo '"\e[C": forward-char' >> /home/jovyan/.inputrc && \
    echo '"\e[D": backward-char' >> /home/jovyan/.inputrc && \
    echo 'Control-l: clear-screen' >> /home/jovyan/.inputrc

# Criar arquivo de configuração do Jupyter para desabilitar o Jedi
RUN mkdir -p /home/jovyan/.jupyter && echo "c.Completer.use_jedi = False" >> /home/jovyan/.jupyter/jupyter_notebook_config.py

# Configurar o terminal no JupyterLab
RUN mkdir -p /home/jovyan/.jupyter/lab/user-settings/@jupyterlab/terminal-extension && \
    echo '{\
    "fontFamily": "monospace",\
    "fontSize": 13,\
    "theme": "dark",\
    "cursorBlink": true,\
    "shutdownOnClose": false,\
    "closeOnExit": false,\
    "scrollback": 1000\
    }' > /home/jovyan/.jupyter/lab/user-settings/@jupyterlab/terminal-extension/plugin.jupyterlab-settings

# Configurar tema Material Darker automaticamente
RUN mkdir -p /home/jovyan/.jupyter/lab/user-settings/@jupyterlab/apputils-extension && \
    echo '{"theme": "Material Darker"}' > /home/jovyan/.jupyter/lab/user-settings/@jupyterlab/apputils-extension/themes.jupyterlab-settings

# Configurar formatação de código
# Install JupyterLab LSP and Python Language Server
RUN pip install jupyterlab-lsp
RUN pip install --no-cache-dir 'python-lsp-server[flake8]'

# Criar arquivo de configuração pycodestyle
RUN echo '[pycodestyle]\n\
max-line-length = 120\n\
ignore = E203, E303, E402\n\
exclude = .git,pycache,.pytest_cache,.tox,venv,*.egg\n\
statistics = True\n\
count = True\
' > /home/jovyan/.config/pycodestyle

RUN mkdir -p /home/jovyan/.jupyter/lab/user-settings/@ryantam626/jupyterlab_code_formatter && \
    echo '{\
    "preferences": {\
        "default_formatter": {\
            "python": ["black", "isort"]\
        }\
    }\
    }' > /home/jovyan/.jupyter/lab/user-settings/@ryantam626/jupyterlab_code_formatter/settings.jupyterlab-settings

# Configurar variáveis de ambiente para o terminal
ENV TERM=xterm-256color
ENV SHELL=/bin/bash

EXPOSE 8888

CMD ["jupyter", "lab", "--ip=*", "--port=8888", "--allow-root", "--no-browser", "--notebook-dir=/project", "--NotebookApp.token=''", "--NotebookApp.password=''", "--NotebookApp.default_url='/lab/tree'"]