FROM python:3.12.2-slim

# Adicionar argumentos para UID/GID do host
ARG UID=1000
ARG GID=1000

# Criar usuário e grupo com UID/GID do host
RUN groupadd -g $GID jovyan && \
    useradd -u $UID -g $GID -m jovyan

# Instalar dependências básicas incluindo sudo
RUN apt-get update && \
    apt-get install -y \
    pciutils wget cmake git build-essential libncurses5-dev libncursesw5-dev libsystemd-dev libudev-dev libdrm-dev pkg-config \
    sudo \
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

# Install JupyterLab LSP and Python Language Server
RUN pip install jupyterlab-lsp
RUN pip install python-lsp-server

# Instalar python-lsp-server com plugins extras
RUN pip install --no-cache-dir \
    'python-lsp-server[all]' \
    pylsp-mypy \
    pyls-flake8 \
    python-lsp-black \
    python-lsp-ruff \
    pylsp-rope

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
WORKDIR /home/jovyan

# Instalar browsers do Playwright e dependências com sudo
RUN playwright install
RUN sudo playwright install-deps

# Criar arquivo de configuração do Jupyter para desabilitar o Jedi
RUN mkdir -p /home/jovyan/.jupyter && echo "c.Completer.use_jedi = False" >> /home/jovyan/.jupyter/jupyter_notebook_config.py

# Configurar tema Material Darker automaticamente
RUN mkdir -p /home/jovyan/.jupyter/lab/user-settings/@jupyterlab/apputils-extension && \
    echo '{"theme": "Material Darker"}' > /home/jovyan/.jupyter/lab/user-settings/@jupyterlab/apputils-extension/themes.jupyterlab-settings

# Configurar formatação de código
RUN mkdir -p /home/jovyan/.jupyter/lab/user-settings/@ryantam626/jupyterlab_code_formatter && \
    echo '{\
    "preferences": {\
        "default_formatter": {\
            "python": ["black", "isort"]\
        }\
    }\
    }' > /home/jovyan/.jupyter/lab/user-settings/@ryantam626/jupyterlab_code_formatter/settings.jupyterlab-settings

# Configurar LSP settings
RUN mkdir -p /home/jovyan/.jupyter/lab/user-settings/@krassowski/jupyterlab-lsp && \
    echo '{\
    "language_servers": {\
        "pylsp": {\
            "serverSettings": {\
                "pylsp.plugins.flake8.enabled": true,\
                "pylsp.plugins.mypy.enabled": true,\
                "pylsp.plugins.mypy.live_mode": true,\
                "pylsp.plugins.pycodestyle.enabled": false,\
                "pylsp.plugins.mccabe.enabled": false,\
                "pylsp.plugins.pyflakes.enabled": false,\
                "pylsp.plugins.ruff.enabled": true\
            }\
        }\
    }\
}' > /home/jovyan/.jupyter/lab/user-settings/@krassowski/jupyterlab-lsp/settings.jupyterlab-settings

# Criar arquivo de configuração mypy
RUN echo '[mypy]\n\
check_untyped_defs = true\n\
disallow_untyped_defs = true\n\
disallow_incomplete_defs = true\n\
disallow_untyped_decorators = true\n\
no_implicit_optional = true\n\
warn_redundant_casts = true\n\
warn_unused_ignores = true\n\
warn_return_any = true\n\
warn_unreachable = true\
' > /home/jovyan/.mypy.ini

# Criar arquivo de configuração flake8
RUN echo '[flake8]\n\
max-line-length = 88\n\
extend-ignore = E203\
' > /home/jovyan/.flake8

EXPOSE 8888

CMD ["jupyter", "lab", "--ip=*", "--port=8888", "--allow-root", "--no-browser", "--notebook-dir=/project", "--NotebookApp.token=''", "--NotebookApp.password=''", "--NotebookApp.default_url='/lab/tree'"]