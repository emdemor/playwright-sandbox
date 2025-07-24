from typing import List, Tuple

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class BrowserSettings(BaseSettings):
    """Configurações do navegador e interações"""

    # Viewport settings
    viewport_width_range: Tuple[int, int] = Field(
        default=(1000, 1920), description="Range de largura do viewport (min, max)"
    )
    viewport_height_range: Tuple[int, int] = Field(
        default=(800, 1080), description="Range de altura do viewport (min, max)"
    )

    # Localization settings
    locales: List[str] = Field(
        default=["pt-BR", "pt-PT", "es-AR", "es-UY", "es-PY"],
        description="Lista de locales disponíveis",
    )

    timezones: List[str] = Field(
        default=[
            "America/Sao_Paulo",
            "America/Rio_Branco",
            "America/Manaus",
            "America/Fortaleza",
            "America/Recife",
            "America/Argentina/Buenos_Aires",
            "America/Montevideo",
        ],
        description="Lista de timezones disponíveis",
    )

    # Mouse scroll settings
    mouse_scroll_moves_range: Tuple[int, int] = Field(
        default=(3, 7), description="Range de movimentos do scroll do mouse"
    )
    mouse_scroll_wheel_moves_range: Tuple[int, int] = Field(
        default=(100, 500),
        description="Range de movimentos da roda do mouse para scroll",
    )
    mouse_scroll_move_sleep_range: Tuple[float, float] = Field(
        default=(0.1, 0.50),
        description="Range de tempo de sleep entre movimentos de scroll",
    )

    # Mouse translate settings
    mouse_translate_moves_range: Tuple[int, int] = Field(
        default=(3, 8), description="Range de movimentos do mouse para tradução"
    )
    mouse_translate_wheel_moves_range: Tuple[int, int] = Field(
        default=(100, 500),
        description="Range de movimentos da roda do mouse para tradução",
    )
    mouse_translate_move_sleep_range: Tuple[float, float] = Field(
        default=(0.1, 0.50),
        description="Range de tempo de sleep entre movimentos de tradução",
    )

    @field_validator("viewport_width_range", "viewport_height_range")
    @classmethod
    def validate_viewport_range(cls, v):
        """Valida se o range do viewport é válido"""
        if len(v) != 2:
            raise ValueError("Range deve ter exatamente 2 valores")
        if v[0] >= v[1]:
            raise ValueError("O primeiro valor deve ser menor que o segundo")
        if v[0] < 0 or v[1] < 0:
            raise ValueError("Valores devem ser positivos")
        return v

    @field_validator("mouse_scroll_moves_range", "mouse_translate_moves_range")
    @classmethod
    def validate_moves_range(cls, v):
        """Valida se o range de movimentos é válido"""
        if len(v) != 2:
            raise ValueError("Range deve ter exatamente 2 valores")
        if v[0] >= v[1]:
            raise ValueError("O primeiro valor deve ser menor que o segundo")
        if v[0] < 1:
            raise ValueError("Número de movimentos deve ser pelo menos 1")
        return v

    @field_validator(
        "mouse_scroll_wheel_moves_range", "mouse_translate_wheel_moves_range"
    )
    @classmethod
    def validate_wheel_moves_range(cls, v):
        """Valida se o range de movimentos da roda é válido"""
        if len(v) != 2:
            raise ValueError("Range deve ter exatamente 2 valores")
        if v[0] >= v[1]:
            raise ValueError("O primeiro valor deve ser menor que o segundo")
        if v[0] < 1:
            raise ValueError("Número de movimentos da roda deve ser pelo menos 1")
        return v

    @field_validator(
        "mouse_scroll_move_sleep_range", "mouse_translate_move_sleep_range"
    )
    @classmethod
    def validate_sleep_range(cls, v):
        """Valida se o range de sleep é válido"""
        if len(v) != 2:
            raise ValueError("Range deve ter exatamente 2 valores")
        if v[0] >= v[1]:
            raise ValueError("O primeiro valor deve ser menor que o segundo")
        if v[0] < 0:
            raise ValueError("Tempo de sleep deve ser positivo")
        return v

    @field_validator("locales")
    @classmethod
    def validate_locales(cls, v):
        """Valida se os locales estão no formato correto"""
        if not v:
            raise ValueError("Lista de locales não pode estar vazia")

        for locale in v:
            if not isinstance(locale, str):
                raise ValueError("Locale deve ser uma string")
            if len(locale.split("-")) != 2:
                raise ValueError(f"Locale '{locale}' deve estar no formato 'xx-XX'")

        return v

    @field_validator("timezones")
    @classmethod
    def validate_timezones(cls, v):
        """Valida se os timezones estão no formato correto"""
        if not v:
            raise ValueError("Lista de timezones não pode estar vazia")

        for timezone in v:
            if not isinstance(timezone, str):
                raise ValueError("Timezone deve ser uma string")
            if not timezone.startswith("America/"):
                raise ValueError(f"Timezone '{timezone}' deve começar com 'America/'")

        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        env_prefix = "BROWSER_"


class ProxySettings(BaseSettings):
    """Configurações de proxy"""

    proxies_file: str = Field(
        default="proxies.txt", description="Nome do arquivo de proxies"
    )

    @field_validator("proxies_file")
    @classmethod
    def validate_proxies_file(cls, v):
        """Valida se o nome do arquivo de proxies é válido"""
        if not v:
            raise ValueError("Nome do arquivo de proxies não pode estar vazio")
        if not v.endswith(".txt"):
            raise ValueError("Arquivo de proxies deve ter extensão .txt")
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        env_prefix = "PROXY_"


# Instâncias globais das configurações
browser_settings = BrowserSettings()
proxy_settings = ProxySettings()
