# AtenteAI

Sistema de agendamento de serviços com dashboard administrativo e automação opcional por agentes de IA.

O projeto é **backend-first**, **manual-first** e foi desenhado para funcionar 100% sem IA, utilizando agentes apenas como automação adicional.

---

## 🎯 Objetivo do Sistema

Permitir o gerenciamento completo de agendas de profissionais, incluindo:

- Cadastro de profissionais e serviços
- Definição de horários recorrentes de atendimento
- Bloqueio de indisponibilidades pontuais
- Criação, reagendamento e cancelamento de compromissos
- Atendimento manual via dashboard
- Atendimento automatizado via agentes de IA (ex: WhatsApp)

---

## 📚 Documentação Oficial (Fonte da Verdade)

> ⚠️ Este README é **apenas informativo**.  
> As regras oficiais do sistema **não vivem aqui**.

A documentação normativa do projeto está na pasta `/specs`:

- **Regras globais e arquiteturais**  
  👉 `specs/constitution.md`

- **Domínio de negócio (agendamentos)**  
  👉 `specs/agendamento.md`

- **Comportamento e limites dos agentes de IA**  
  👉 `specs/agente-ia.md`

Em caso de conflito:
> **As specs sempre prevalecem sobre este README.**

---

## 🧱 Arquitetura (Visão Geral)

O sistema é composto por três camadas independentes:

1. **Backend (Core / API REST)**  
   - Fonte única da verdade
   - Contém toda a lógica de negócio e validações

2. **Frontend (Dashboard Administrativo)**  
   - Interface humana para operação manual
   - Funciona completamente sem IA

3. **Agentes de IA (Opcional)**  
   - Atuam como clientes da API
   - Automatizam atendimento e agendamentos
   - Nunca acessam o banco diretamente

---

## 🛠️ Stack Tecnológica (Resumo)

### Backend
- FastAPI (Python, async)
- PostgreSQL
- SQLAlchemy + Alembic
- Pydantic v2

### Frontend
- React + Vite + TypeScript
- TanStack Query
- Zustand
- Tailwind CSS

### IA / Automação
- LangGraph
- LangChain
- LLM configurável (ex: Gemini, GPT, Claude)

---

## 🧪 Estilo de Desenvolvimento

Este projeto segue um **workflow rigorosamente incremental e orientado à aprovação**:

- Uma mudança por vez
- Explicação antes de implementação
- Aprovação explícita antes de qualquer modificação
- Prioridade em clareza, aprendizado e validação

As preferências de workflow para assistentes de IA estão descritas em um arquivo próprio na raiz do projeto.

---

## ▶️ Como rodar o projeto (exemplo)

> ⚠️ Ajuste conforme o estado atual do projeto

```bash
# Backend
cd backend
uvicorn main:app --reload

# Frontend
cd frontend
npm install
npm run dev
