"""
LLM Factory - Abstração centralizada para múltiplos providers de LLM.

Este módulo implementa o Factory Pattern para gerenciar diferentes providers
de LLM de forma centralizada, permitindo trocar entre providers apenas
alterando variáveis no arquivo .env.

Providers Suportados:
    - groq: ChatGroq (padrão, rápido, gratuito, remoto)
    - ollama: ChatOllama (local, privado, sem custo de API)
    - openai: ChatOpenAI (GPT-4, etc)
    - anthropic: ChatAnthropic (Claude)

Uso:
    from app.core.llm_factory import get_llm
    
    # Usa automaticamente o provider configurado no .env
    llm = get_llm()
    response = await llm.ainvoke(messages)

Configuração (.env):
    # Para usar Groq (padrão)
    DEFAULT_LLM_PROVIDER=groq
    DEFAULT_MODEL=llama-3.3-70b-versatile
    GROQ_API_KEY=gsk_...
    
    # Para usar Ollama local
    DEFAULT_LLM_PROVIDER=ollama
    OLLAMA_MODEL=llama3.1:8b
    OLLAMA_BASE_URL=http://localhost:11434
"""

from langchain_core.language_models import BaseChatModel
from app.core.config import settings


def get_llm() -> BaseChatModel:
    """
    Factory que retorna o LLM configurado baseado em DEFAULT_LLM_PROVIDER.
    
    Esta função centraliza a criação de instâncias de LLM, eliminando
    duplicação de código e permitindo trocar de provider facilmente.
    
    O provider é determinado pela variável DEFAULT_LLM_PROVIDER no .env.
    
    Returns:
        BaseChatModel: Instância do LLM configurado (ChatGroq, ChatOllama, etc)
        
    Raises:
        ValueError: Se o provider não é suportado ou credenciais estão faltando
        
    Examples:
        >>> llm = get_llm()  # Usa DEFAULT_LLM_PROVIDER do .env
        >>> response = await llm.ainvoke([HumanMessage(content="Olá")])
    """
    
    provider = settings.DEFAULT_LLM_PROVIDER.lower()
    
    # 🚀 GROQ - Rápido, gratuito, remoto (padrão)
    if provider == "groq":
        if not settings.GROQ_API_KEY:
            raise ValueError(
                "GROQ_API_KEY não encontrada no .env. "
                "Adicione: GROQ_API_KEY=gsk_..."
            )
        
        from langchain_groq import ChatGroq
        
        return ChatGroq(
            model=settings.DEFAULT_MODEL,
            temperature=settings.TEMPERATURE,
            groq_api_key=settings.GROQ_API_KEY,
            max_retries=3,
            timeout=30,
        )
    
    # 🦙 OLLAMA - Local, privado, sem custo de API
    elif provider == "ollama":
        from langchain_ollama import ChatOllama
        
        print(f"🦙 Usando Ollama local: {settings.OLLAMA_BASE_URL}")
        print(f"📦 Modelo: {settings.OLLAMA_MODEL}")
        
        return ChatOllama(
            model=settings.OLLAMA_MODEL,
            temperature=settings.TEMPERATURE,
            base_url=settings.OLLAMA_BASE_URL
        )
    
    # 🤖 OPENAI - GPT-4, GPT-3.5, etc
    elif provider == "openai":
        if not settings.OPENAI_API_KEY:
            raise ValueError(
                "OPENAI_API_KEY não encontrada no .env. "
                "Adicione: OPENAI_API_KEY=sk-..."
            )
        
        from langchain_openai import ChatOpenAI
        
        return ChatOpenAI(
            model=settings.DEFAULT_MODEL,
            temperature=settings.TEMPERATURE,
            api_key=settings.OPENAI_API_KEY
        )
    
    # 🧠 ANTHROPIC - Claude 3, etc
    elif provider == "anthropic":
        if not settings.ANTHROPIC_API_KEY:
            raise ValueError(
                "ANTHROPIC_API_KEY não encontrada no .env. "
                "Adicione: ANTHROPIC_API_KEY=sk-ant-..."
            )
        
        from langchain_anthropic import ChatAnthropic
        
        return ChatAnthropic(
            model=settings.DEFAULT_MODEL,
            temperature=settings.TEMPERATURE,
            api_key=settings.ANTHROPIC_API_KEY
        )
    
    else:
        raise ValueError(
            f"Provider '{provider}' não suportado. "
            f"Use: 'groq', 'ollama', 'openai', ou 'anthropic'"
        )


def get_llm_info() -> dict:
    """
    Retorna informações sobre o LLM atual configurado.
    
    Útil para debugging, logs e verificação de configuração.
    
    Returns:
        dict: Dicionário com provider, modelo, temperatura, etc
        
    Examples:
        >>> info = get_llm_info()
        >>> print(f"Usando {info['provider']} com {info['model']}")
        Usando groq com llama-3.3-70b-versatile
    """
    
    provider = settings.DEFAULT_LLM_PROVIDER.lower()
    
    info = {
        "provider": provider,
        "temperature": settings.TEMPERATURE,
    }
    
    if provider == "groq":
        info["model"] = settings.DEFAULT_MODEL
        info["api_key_set"] = bool(settings.GROQ_API_KEY)
        
    elif provider == "ollama":
        info["model"] = settings.OLLAMA_MODEL
        info["base_url"] = settings.OLLAMA_BASE_URL
        
    elif provider == "openai":
        info["model"] = settings.DEFAULT_MODEL
        info["api_key_set"] = bool(settings.OPENAI_API_KEY)
        
    elif provider == "anthropic":
        info["model"] = settings.DEFAULT_MODEL
        info["api_key_set"] = bool(settings.ANTHROPIC_API_KEY)
    
    return info
