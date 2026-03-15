# ============================================
# Backend — FastAPI + LangGraph Agent
# ============================================
FROM python:3.12-slim

# Evitar prompts interativos e buffering
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Dependências do sistema (necessárias para asyncpg, psycopg2)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Instalar requirements primeiro (cache de camadas)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar código da aplicação
COPY alembic.ini .
COPY alembic/ alembic/
COPY app/ app/

# Porta do FastAPI
EXPOSE 8000

# Rodar migrations e iniciar servidor
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2"]
