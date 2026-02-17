"""
Marketing CRM - Sistema de Agendamento com IA
Entry point da aplicação FastAPI
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.authControllers import router as auth_router
from app.api.userControllers import router as user_router
from app.api.clientsControllers import router as clients_router
from app.api.appointmentControllers import router as appointments_router
from app.api.chatControllers import router as chat_router

# Criar instância do FastAPI
app = FastAPI(
    title="Marketing CRM API",
    version="0.1.0",
    description="Sistema de agendamento de reuniões para agência de marketing com IA via WhatsApp",
    debug=settings.DEBUG
)

# Configurar CORS (permitir frontend acessar o backend)
# Em produção, defina CORS_ORIGINS com a URL do frontend (ex: https://ia-crm-atenteai.netlify.app)
cors_origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "https://ia-crm-atenteai.netlify.app",
]

# Adicionar origens extras de produção via variável de ambiente
extra_origins = os.environ.get("CORS_ORIGINS", "")
if extra_origins:
    cors_origins.extend([o.strip() for o in extra_origins.split(",") if o.strip()])

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Endpoint raiz - verificação básica"""
    return {
        "message": "Marketing CRM API is running",
        "version": "0.1.0",
        "status": "healthy"
    }


@app.get("/health")
async def health_check():
    """Health check para monitoramento"""
    return {
        "status": "healthy",
        "service": "marketing-crm-backend"
    }


@app.get("/debug/groq")
async def debug_groq():
    """Debug: testa conexão com Groq API"""
    import httpx
    import socket
    
    results = {}
    
    # Teste 1: DNS
    try:
        ip = socket.getaddrinfo("api.groq.com", 443)
        results["dns"] = f"OK - {ip[0][4][0]}"
    except Exception as e:
        results["dns"] = f"ERRO - {e}"
    
    # Teste 2: HTTPS direto
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get("https://api.groq.com")
            results["https"] = f"OK - status {resp.status_code}"
    except Exception as e:
        results["https"] = f"ERRO - {type(e).__name__}: {e}"
    
    # Teste 3: Groq API
    try:
        from app.core.config import settings
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
                json={"model": settings.DEFAULT_MODEL, "messages": [{"role": "user", "content": "oi"}], "max_tokens": 5}
            )
            results["groq_api"] = f"OK - status {resp.status_code}"
    except Exception as e:
        results["groq_api"] = f"ERRO - {type(e).__name__}: {e}"
    
    return results


# Importar routers



# Registrar routers
app.include_router(auth_router, prefix="/api/v1")
app.include_router(user_router, prefix="/api/v1")
app.include_router(clients_router, prefix="/api/v1")
app.include_router(appointments_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
