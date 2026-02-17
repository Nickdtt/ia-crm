FROM python:3.12-slim

WORKDIR /app

# Instalar dependências de sistema (gcc para compilação, ca-certificates para SSL/HTTPS)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && update-ca-certificates

# Instalar PyTorch CPU-only ANTES dos requirements (evita puxar CUDA ~3GB)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Copiar e instalar dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código do backend
COPY . .

# Expor porta
EXPOSE 8000

# Comando de inicialização
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
