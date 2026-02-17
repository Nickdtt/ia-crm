"""
Marketing CRM - Sistema de Agendamento com IA
Entry point da aplicação FastAPI
"""

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
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Frontend Next.js
        "http://localhost:5173",  # Frontend Vite
    ],
    allow_credentials=True,
    allow_methods=["*"],  # Permitir todos os métodos (GET, POST, etc)
    allow_headers=["*"],  # Permitir todos os headers
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


# Importar routers



# Registrar routers
app.include_router(auth_router, prefix="/api/v1")
app.include_router(user_router, prefix="/api/v1")
app.include_router(clients_router, prefix="/api/v1")
app.include_router(appointments_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
