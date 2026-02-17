# 🤖 AtenteAI — CRM com Agente de IA

Sistema completo de CRM com agendamento inteligente, dashboard administrativo responsivo e agente conversacional com IA para captação de leads e agendamento automatizado.

---

## ✨ Funcionalidades

- **Dashboard Administrativo** — Painel responsivo (Mobile/Tablet/Desktop) com visão geral de clientes, agendamentos e métricas
- **Gestão de Clientes** — CRUD completo com segmentação, orçamento, telefone e email
- **Calendário de Agendamentos** — Grade semanal (desktop) ou diária (mobile) com criação e cancelamento
- **Agente Conversacional IA** — Chat que coleta leads e agenda reuniões automaticamente via linguagem natural
- **Autenticação JWT** — Login seguro com token para acesso ao dashboard
- **Multi-LLM** — Suporte a Groq, OpenAI, Anthropic, Google Gemini e Ollama (local)

---

## 🧱 Arquitetura

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Frontend   │────▶│   Backend    │────▶│ PostgreSQL  │
│  React/Vite │     │   FastAPI    │     │  (Supabase) │
└─────────────┘     └──────┬───────┘     └─────────────┘
                           │
                    ┌──────┴───────┐
                    │  LangGraph   │
                    │  AI Agent    │
                    └──────────────┘
```

1. **Backend (FastAPI)** — API REST, validações, lógica de negócio
2. **Frontend (React + Vite)** — Dashboard responsivo, chat com IA
3. **Agente IA (LangGraph)** — Grafo conversacional que coleta leads e agenda reuniões

---

## 🛠️ Stack Tecnológica

| Camada | Tecnologia |
|--------|-----------|
| **Backend** | FastAPI, SQLAlchemy (async), Alembic, Pydantic v2 |
| **Frontend** | React 19, Vite, TypeScript, TanStack Query, Zustand, Tailwind CSS 4 |
| **IA** | LangGraph, LangChain, Groq/OpenAI/Gemini/Anthropic/Ollama |
| **Banco** | PostgreSQL (Supabase ou local) |
| **Auth** | JWT (PyJWT + passlib/bcrypt) |

---

## 🚀 Como Rodar

### Pré-requisitos
- Python 3.12+
- Node.js 20+
- PostgreSQL (ou conta Supabase)

### 1. Clone e configure
```bash
git clone https://github.com/SEU_USUARIO/ia-crm.git
cd ia-crm
cp .env.example .env
# Edite .env com suas credenciais
```

### 2. Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
python scripts/create_admin.py
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend
```bash
cd frontend
npm install
npm run dev
```

### 4. Acesse
- **Dashboard:** http://localhost:5173
- **API Docs:** http://localhost:8000/docs
- **Chat IA:** http://localhost:5173/chat

---

## 📁 Estrutura do Projeto

```
├── backend/
│   ├── app/
│   │   ├── agent/         # LangGraph: grafo, nós, estado
│   │   ├── models/        # SQLAlchemy models
│   │   ├── routes/        # FastAPI endpoints
│   │   ├── schemas/       # Pydantic schemas
│   │   └── services/      # Lógica de negócio
│   ├── alembic/           # Migrations
│   ├── scripts/           # Scripts auxiliares
│   ├── tests/             # Testes
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/    # Modais reutilizáveis
│   │   ├── hooks/         # React Query hooks
│   │   ├── layouts/       # AdminLayout responsivo
│   │   ├── pages/         # Dashboard, Clients, Appointments, Chat
│   │   └── services/      # API client (Axios)
│   └── package.json
├── specs/                 # Documentação normativa
├── .env.example           # Template de variáveis
└── README.md
```

---

## 🧪 Testes

```bash
cd backend
source venv/bin/activate

# Testes de stress do agente (requer backend rodando)
python tests/test_agent_stress.py

# Testes de serviço
pytest tests/
```

---

## 📄 Licença

MIT
