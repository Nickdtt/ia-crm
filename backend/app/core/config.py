from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from pathlib import Path

# Caminho para o .env na raiz do projeto (um nível acima de backend)
ENV_FILE = Path(__file__).parent.parent.parent.parent / ".env"
# Em produção (Railway/Render) o .env não existe — as variáveis vêm do sistema
ENV_FILE_PATH = str(ENV_FILE) if ENV_FILE.exists() else None


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    Security Features:
    ------------------
    - Secrets (API keys, DATABASE_URL, SECRET_KEY) are protected with repr=False
    - print(settings) não expõe valores sensíveis
    - settings.model_dump() por padrão oculta secrets (use include_secrets=True para acesso interno)
    - Valores sensíveis acessíveis normalmente: settings.GROQ_API_KEY (quando necessário)
    
    Examples:
    ---------
    >>> settings = get_settings()
    >>> print(settings)  # Safe: não mostra secrets
    Settings(APP_NAME='AtenteAI', DEBUG=True, ...)
    
    >>> settings.model_dump()  # Safe: secrets ocultos
    {'GROQ_API_KEY': '***HIDDEN***', ...}
    
    >>> settings.GROQ_API_KEY  # OK: acesso direto quando necessário
    'gsk_...'
    """
    
    # Application
    APP_NAME: str = "Isso não é uma agência"
    DEBUG: bool = True
    
    # Database
    DATABASE_URL: str = Field(..., repr=False)
    
    # API Keys
    OPENAI_API_KEY: str | None = Field(default=None, repr=False)
    ANTHROPIC_API_KEY: str | None = Field(default=None, repr=False)
    GOOGLE_API_KEY: str | None = Field(default=None, repr=False)
    GROQ_API_KEY: str | None = Field(default=None, repr=False)
    EVOLUTION_API_KEY: str = Field(default="THISISMYSECURETOKEN", repr=False)
    
    # JWT
    SECRET_KEY: str = Field(..., repr=False)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # LLM Configuration
    DEFAULT_LLM_PROVIDER: str = "groq"  # Options: "groq", "ollama", "openai", "anthropic"
    DEFAULT_MODEL: str = "meta-llama/llama-4-scout-17b-16e-instruct"
    TEMPERATURE: float = 0.7
    
    # Ollama Configuration (usado quando DEFAULT_LLM_PROVIDER = "ollama")
    OLLAMA_BASE_URL: str = "http://localhost:11434"  # URL padrão do Ollama
    OLLAMA_MODEL: str = "llama3.1:8b"  # Exemplos: llama3.1:8b, mistral, phi3, qwen2.5
    
    model_config = SettingsConfigDict(
        env_file=ENV_FILE_PATH,
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )
    
    def __repr__(self) -> str:
        """Representação segura que não expõe secrets."""
        return (
            f"Settings("
            f"APP_NAME={self.APP_NAME!r}, "
            f"DEBUG={self.DEBUG}, "
            f"DEFAULT_LLM_PROVIDER={self.DEFAULT_LLM_PROVIDER!r}, "
            f"DEFAULT_MODEL={self.DEFAULT_MODEL!r}"
            f")"
        )
    
    def __str__(self) -> str:
        """String representation segura."""
        return self.__repr__()
    
    def model_dump(self, **kwargs) -> dict:
        """
        Override para proteger secrets ao fazer dump do modelo.
        Remove campos sensíveis por padrão.
        """
        # Se mode='json' ou include_secrets=True explicitamente, permite dump completo
        if kwargs.get('include_secrets'):
            kwargs.pop('include_secrets')
            return super().model_dump(**kwargs)
        
        # Por padrão, remove campos sensíveis
        data = super().model_dump(**kwargs)
        
        # Remove secrets
        secrets = [
            'DATABASE_URL', 'OPENAI_API_KEY', 'ANTHROPIC_API_KEY',
            'GOOGLE_API_KEY', 'GROQ_API_KEY', 'EVOLUTION_API_KEY', 'SECRET_KEY'
        ]
        
        for secret in secrets:
            if secret in data:
                data[secret] = '***HIDDEN***' if data[secret] else None
        
        return data


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
