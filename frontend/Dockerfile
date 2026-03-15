# ============================================
# Frontend — Vite React (multi-stage build)
# ============================================

# Stage 1: Build
FROM node:20-alpine AS builder

WORKDIR /app

# Instalar dependências primeiro (cache de camadas)
COPY package.json package-lock.json ./
RUN npm ci

# Build arg para injetar URL da API em tempo de build
ARG VITE_API_URL=https://api.ineua.com.br
ENV VITE_API_URL=$VITE_API_URL

# Copiar código e buildar
COPY . .
RUN npm run build

# Stage 2: Servir com nginx
FROM nginx:alpine

# Copiar config customizada do nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copiar build estático
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
