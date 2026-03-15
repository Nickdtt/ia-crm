@@
# CONTEXTO_DESENVOLVIMENTO_GRAPH_AGENT.md

**Última atualização:** 09/02/2026  
**Progresso geral:** 95% (Sistema WhatsApp + LangGraph funcional em produção)
## 🚨 INCIDENTE RECENTE: BANCO DE PRODUÇÃO

Em 07/02/2026, durante execução de testes automatizados, o banco de produção (Supabase) foi acidentalmente apagado devido ao uso de `drop_all()` em teardown de testes com a URL de produção. Todas as tabelas foram removidas, exceto `alembic_version`.

**Procedimento de restauração:**
- Recriação manual de todas as tabelas via `Base.metadata.create_all()` com todos os models importados.
- Sincronização do estado das migrations com `alembic stamp head`.
- Execução do script `create_admin.py` para recriar o usuário admin.
- Validação dos endpoints e fluxos principais.

**Lições aprendidas:**
- Nunca rodar testes apontando para o banco de produção.
- Sempre isolar ambientes de teste e produção (variáveis de ambiente, .env separado, CI/CD seguro).
- Testes automatizados devem usar banco local ou de staging, nunca produção.
- O teardown de testes com `drop_all()` é perigoso e deve ser protegido por checagem de ambiente.
- Documentar e revisar scripts de teste e fixtures.

**Status:** Banco restaurado, admin recriado, sistema operacional. Nenhuma informação sensível de clientes foi perdida, pois o ambiente estava em fase de testes.

---
## 🔄 NOVA LÓGICA DE REUSO DE SLOTS (AGENDAMENTOS)

**Implementação:**
- O backend agora ignora agendamentos com status `CANCELLED` ao validar conflitos de horário.
- Slots de horários de agendamentos cancelados ficam imediatamente disponíveis para novos agendamentos.
- Testes automatizados criados para garantir que:
  - Não é possível agendar dois compromissos no mesmo horário (exceto se um for cancelado).
  - Após cancelar um agendamento, o slot fica livre e pode ser reutilizado.
  - Reagendamento e cancelamento funcionam conforme esperado.

**Recomendações:**
- Sempre validar status dos agendamentos ao consultar disponibilidade.
- Testes de slot reuse devem ser mantidos e expandidos.

---

---

## 📊 STATUS ATUAL

**Sistema em produção:** WhatsApp CRM via Evolution API + LangGraph Agent + PostgreSQL ✅  
**Próximo passo:** Ajustes finos (extração precisa de data/hora, link Google Meet real)  
**Bloqueios:** Nenhum

---

## ✅ CONCLUÍDO E FUNCIONAL

### 1. Database & Infrastructure

### 1.1 Frontend: Descrição e Implementações Recentes (fev/2026)

- **Resumo geral:** Descrição completa do frontend, suas convenções, fluxos e próximos passos.

- **Framework e Build:** React 19 + TypeScript; Vite, ESLint, `tsconfig`.

- **Principais Implementações recentes:**
  - **ClientModal (edição):** Modal reutilizável para criação e edição de clientes com validação, integração com API e feedback visual.
  - **Botão de cancelamento de agendamento:** Botão "Cancelar" nos cards/listagem; cancelamento faz o slot ficar disponível imediatamente (reflete a lógica do backend).
  - **Sincronização e UX:** Uso de TanStack Query para atualização automática após mutações; toasts/loaders para feedback.

- **Arquitetura de componentes:** Componentização por domínio (forms, modals, tables), tipagem forte com TypeScript.

- **Testes:** Fluxos de edição, cancelamento e reuso de slots validados manualmente; testes automatizados de componentes e integração pendentes.

- **Próximos passos frontend:** Página de calendário/admin para bloqueios, testes automatizados, melhorias de UX/UI e documentação para admin.

---
- ✅ **PostgreSQL** async com asyncpg (port 5434)
- ✅ **Models SQLAlchemy** (2 entidades principais):
  - `User` (admin only: email, hashed_password, role)
  - `Client` (leads qualificados: first_name, last_name, phone, email, company_name, segment, monthly_budget, main_marketing_problem)
  - `Appointment` (reuniões: client_id FK, scheduled_at, duration_minutes=40, meeting_type="CONSULTORIA_INICIAL", status)
- ✅ **Alembic** migrations funcionando
- ✅ **AsyncSessionLocal** para sessões por request

### 2. Schemas Pydantic (Validação de Dados)
Todos localizados em `app/schemas/`:
- ✅ `userSchema.py` (UserCreate, UserUpdate, UserResponse)
- ✅ `clientSchema.py` (ClientCreate com ClientSegment enum, ClientUpdate, ClientResponse)
- ✅ `appointmentSchema.py` (AppointmentCreate com validação de data futura, AppointmentResponse)
- ✅ `authSchema.py` (LoginRequest, TokenResponse, RefreshRequest)

**ClientSegment enum:** CLINICA_MEDICA, CLINICA_ODONTOLOGICA, PSICOLOGO, FISIOTERAPEUTA, FARMACIA, LABORATORIO, HOME_CARE, CLINICA_ESTETICA, NUTRICAO, VETERINARIA, HOSPITAL, PLANO_SAUDE, CLINICA_OCUPACIONAL, CLINICA_REABILITACAO, OUTRO

### 3. Services (Lógica de Negócio)
Todos localizados em `app/services/`:

#### `userService.py` (5 funções - testadas ✅)
- `create_user(data, db)` - Cria usuário com hash de senha
- `get_user(user_id, db)` - Busca por ID
- `get_user_by_email(email, db)` - Busca por email
- `update_user(user_id, data, db)` - Atualização parcial
- `delete_user(user_id, db)` - Soft delete (is_active=False)

#### `clientService.py` (6 funções - testadas ✅)
- `create_client(data, db)` - Cria cliente (valida phone único)
- `get_client(client_id, db)` - Busca por ID
- `get_client_by_phone(phone, db)` - Busca por telefone (usado pelo agent)
- `list_clients(db)` - Lista todos
- `update_client(client_id, data, db)` - Atualização parcial
- `delete_client(client_id, db)` - Hard delete

#### `appointmentService.py` (11 funções - testadas ✅)
- `create_appointment(data, db)` - Cria agendamento (valida data futura)
- `get_appointment_by_id(appointment_id, db)` - Busca por ID
- `update_appointment(appointment_id, data, db)` - Atualiza agendamento existente
- `cancel_appointment(appointment_id, reason, db)` - Cancela agendamento
- `update_appointment_status(appointment_id, status, db)` - Atualiza status (PENDING → CONFIRMED → COMPLETED)
- `list_appointments_by_client(client_id, db)` - Lista agendamentos de um cliente
- `list_all_appointments(db, status=None)` - Lista todos (admin dashboard)
- `get_available_slots(target_date, db)` - **Retorna horários livres** (9h-18h, seg-sex)
- `block_full_day(target_date, db)` - **Bloqueia dia inteiro** (férias, feriados)
- `block_shift(target_date, shift, db)` - **Bloqueia turno** (morning/afternoon)
- `unblock_date(target_date, db)` - **Remove bloqueios** de uma data

#### `authService.py` (5 funções - testadas ✅)
- `hash_password(password)` - Gera hash bcrypt
- `verify_password(plain, hashed)` - Verifica senha contra hash
- `authenticate_user(email, password, db)` - Valida credenciais
- `create_access_token(user_id, role, expires_delta_minutes=None)` - Gera JWT
  - Sem `expires_delta_minutes`: 30 min (access token)
  - Com `expires_delta_minutes=10080`: 7 dias (refresh token)
  - ⚠️ Usa `datetime.now(timezone.utc)` (corrigido deprecation warning)
- `verify_token(token)` - Valida e decodifica JWT

### 4. API Layer
Localizados em `app/api/`:

#### `dependencies.py` (3 funções - testadas ✅)
- `get_db()` - Injeta AsyncSession
- `get_current_user(credentials: HTTPBearer)` - Valida JWT, retorna payload com user_id + role
- `require_role(required_role: str)` - Factory que retorna dependência validando role

#### `authControllers.py` (2 endpoints - testados ✅)
```python
POST /auth/login
Body: {"email": "...", "password": "..."}
Response: {"access_token": "...", "refresh_token": "...", "token_type": "bearer"}

POST /auth/refresh
Body: {"refresh_token": "..."}
Response: {"access_token": "...", "refresh_token": "...", "token_type": "bearer"}
```

#### `clientsControllers.py` (CRUD básico - admin only)
```python
GET /api/v1/clients/ - Lista clientes (admin only)
POST /api/v1/clients/ - Cria cliente (admin only)
GET /api/v1/clients/{client_id} - Busca cliente por ID (admin only)
PUT /api/v1/clients/{client_id} - Atualiza cliente (admin only)
DELETE /api/v1/clients/{client_id} - Deleta cliente (admin only)
```

#### `userControllers.py` (CRUD completo - testado via curl)
```python
GET /api/v1/users/ - Lista usuários (admin only)
POST /api/v1/users/ - Cria usuário (admin only)
GET /api/v1/users/{user_id} - Busca usuário (admin ou próprio)
PUT /api/v1/users/{user_id} - Atualiza usuário (admin ou próprio)
DELETE /api/v1/users/{user_id} - Deleta usuário (admin only)
```

~~professionalsControllers.py, servicesControllers.py~~ (removidos)

### 5. LangGraph Multi-Agent System ⭐ **PRODUÇÃO**
**Status:** 95% completo - funcional end-to-end em produção via WhatsApp

#### Arquitetura
- **15+ nodes:** greeting, intent_analyzer, question_answerer, qualification_agent, budget_filter, ask_to_schedule, datetime_collector, slot_checker, alternative_slots, appointment_creator, confirmation, fallback, thankyou
- **Entry point dinâmico:** conversation_mode determina qual node executar
- **State Management:** MarketingCRMState com 20+ campos de controle
- **LLM:** OpenAI GPT-4 via langchain (para classificação de intenção e extração de dados)
- **WhatsApp:** Evolution API v2 (localhost:8080)

#### State Global (MarketingCRMState)
```python
class MarketingCRMState(TypedDict):
    conversation_mode: str  # qualification | scheduling | question | completed
    messages: list[str]
    user_input: str
    agent_response: str
    phone: str  # 71991186382
    client_id: Optional[str]
    client_data: dict  # 7 campos de qualificação
    qualification_complete: bool
    budget_qualified: bool
    schedule_offered: bool
    wants_to_schedule: bool
    requested_datetime: Optional[datetime]
    slot_available: bool
    alternative_slots: list[dict]
    appointment_id: Optional[str]
    permission_asked: bool
```

#### Nodes Implementados (15+)

**1. GREETING** - Apresenta agência na primeira mensagem  
**2. INTENT_ANALYZER** - Classifica se lead quer reunião ou tem perguntas (LLM)  
**3. QUESTION_ANSWERER** - Responde FAQs sobre serviços e pede permissão para qualificar (LLM)  
**4. QUALIFICATION_AGENT** - Coleta 7 campos progressivamente:
   - `first_name`, `last_name`, `email` (opcional), `company_name`, `segment` (enum), `monthly_budget`, `main_marketing_problem`
   - **UMA pergunta por vez** (progressive disclosure)
   - Extrai dados com LLM: "João Silva" → first_name="João", last_name="Silva"
   - Budget parsing: "6 mil reais" → Decimal(6000.00)
   - Segment mapping: "clínica odontológica" → ClientSegment.CLINICA_ODONTOLOGICA
   - Cria `Client` no banco quando completo

**5. BUDGET_FILTER** - Valida orçamento >= R$ 3.000 (regra de negócio)  
**6. ASK_TO_SCHEDULE** - Oferece reunião de 40 min via Google Meet  
**7. DATETIME_COLLECTOR** - Extrai data/hora da mensagem do usuário (LLM)  
**8. SLOT_CHECKER** - Verifica disponibilidade no banco (conflito de horário)  
**9. ALTERNATIVE_SLOTS** - Sugere 3 horários alternativos se ocupado  
**10. APPOINTMENT_CREATOR** - Cria `Appointment` no banco (40 min, CONSULTORIA_INICIAL)  
**11. CONFIRMATION** - Mensagem de sucesso com resumo + link Google Meet  
**12. FALLBACK** - Mensagem quando orçamento < R$ 3.000  
**13. THANKYOU** - Mensagem quando lead recusa agendamento

#### Funcionalidades Validadas
- ✅ **Conversação progressiva:** Uma pergunta por vez, nunca sobrecarga cognitiva
- ✅ **Extração inteligente de dados:** LLM parseia nomes, segmentos, orçamentos
- ✅ **Detecção de budget:** Suporta "R$ 6.000", "6000", "6 mil reais"
- ✅ **Mapeamento de segment:** 15 opções de ClientSegment enum
- ✅ **Criação automática:** Client + Appointment no PostgreSQL
- ✅ **Validação de horário:** Verifica conflitos no banco (40 min de overlap)
- ✅ **Horários alternativos:** Lista 3 próximos slots livres
- ✅ **Entry point dinâmico:** Preserva contexto entre mensagens
- ✅ **Controle de concorrência:** asyncio.Lock por remote_jid (evita race conditions)
- ✅ **Simulação de digitação:** 2-15s baseado no comprimento da mensagem
- ✅ **Presença WhatsApp:** Envia "composing" → sleep → "paused" → mensagem

#### Integração WhatsApp (Evolution API v2)
```python
# Webhook recebe mensagens
POST /webhook/whatsapp
- Filtra números da lista branca (testes)
- Extrai remote_jid (71991186382@s.whatsapp.net)
- Mantém state por usuário (defaultdict)
- Controle de concorrência (asyncio.Lock)
- Chama marketing_crm_graph.ainvoke(state)
- Simula digitação (enviar_presence + sleep + enviar_mensagem)

# Envia presença "digitando..."
POST /chat/sendPresence/{instance}
Body: {"number": "5571991186382@s.whatsapp.net", "delay": 3000, "presence": "composing"}

# Envia mensagem
POST /message/sendText/{instance}
Body: {"number": "5571991186382", "text": "Resposta do agent"}
```

**Cálculo de delay dinâmico:**
```python
tempo_base = random.uniform(2.0, 4.0)  # 2-4 segundos
tempo_caracteres = len(resposta) / 10 * 0.5  # +0.5s a cada 10 chars
tempo_total = max(2.0, min(15.0, tempo_base + tempo_caracteres))  # 2-15s
delay_ms = int(tempo_total * 1000)
```

#### Fluxos de Uso Testados
- ✅ Lead quer reunião diretamente → qualificação → budget ok → agendamento confirmado
- ✅ Lead tem perguntas → responde FAQ → pede permissão → qualificação → agendamento
- ✅ Orçamento insuficiente (< R$ 3k) → fallback com mensagem educada
- ✅ Horário ocupado → sugere 3 alternativas → escolhe → cria agendamento
- ✅ Lead recusa agendamento → thankyou mantendo porta aberta
- ✅ Cliente existente (telefone duplicado) → recupera do banco ao invés de criar

#### Arquivos do Agent
```
backend/app/agent/
├── graph.py ✅ - Monta workflow com 15+ nodes e edges condicionais
├── state.py ✅ - MarketingCRMState com 20 campos
└── nodes/
    ├── greeting.py ✅
    ├── intent_analyzer.py ✅
    ├── question_answerer.py ✅
    ├── qualification_agent.py ✅
    ├── budget_filter.py ✅
    ├── ask_to_schedule.py ✅
    ├── datetime_collector.py ✅
    ├── slot_checker.py ✅
    ├── alternative_slots.py ✅
    ├── appointment_creator.py ✅
    ├── confirmation.py ✅
    └── fallback.py ✅ (inclui thankyou_node)

backend/app/api/
├── whatsappControllers.py ✅ - Webhook handler + simulação de digitação
```

#### Ajustes Finos Pendentes
- [ ] Extração precisa de data/hora (LLM parsing de "amanhã às 14h")
- [ ] Geração de link Google Meet real (via Google Calendar API)
- [ ] Envio de email de confirmação (template HTML)
- [ ] Tratamento de edge cases:
  - Agendamento duplicado (mesmo cliente em horário próximo)
  - Cliente muda de ideia durante qualificação
- [ ] Fine-tuning de prompts (tom mais objetivo)

### 6. WhatsApp Integration (Evolution API v2) ⭐ **PRODUÇÃO**
**Stack:** Evolution API (Docker localhost:8080) + FastAPI webhook + LangGraph Agent

**Endpoints configurados:**
```python
# Webhook configurado no Evolution API
Webhook URL: http://localhost:8000/webhook/whatsapp
Events: messages.upsert

# FastAPI recebe mensagens
POST /webhook/whatsapp
- Valida payload do Evolution API
- Filtra números da lista branca (71991186382, 71991797102)
- Extrai remote_jid: 5571991186382@s.whatsapp.net
- Extrai texto: payload["data"]["message"]["conversation"]
- Normaliza telefone: 557191186382 → 71991186382
- Mantém state por usuário (defaultdict)
- Controle de concorrência: asyncio.Lock por remote_jid
- Chama: await marketing_crm_graph.ainvoke(state)
- Extrai resposta: result["agent_response"]
- Simula digitação + envia resposta

# Evolution API - Envia presença "digitando..."
POST http://localhost:8080/chat/sendPresence/{instance}
Body: {
    "number": "5571991186382@s.whatsapp.net",
    "delay": 3000,
    "presence": "composing"  # ou "paused"
}

# Evolution API - Envia mensagem
POST http://localhost:8080/message/sendText/{instance}
Body: {
    "number": "5571991186382",
    "text": "Resposta do agent"
}
```

**Fluxo completo testado:**
1. Mensagem enviada do WhatsApp → Evolution API recebe
2. Evolution API envia webhook → FastAPI `/webhook/whatsapp`
3. FastAPI filtra número, extrai texto, recupera/cria state
4. FastAPI chama `marketing_crm_graph.ainvoke(state)`
5. Agent processa (15+ nodes), retorna `agent_response`
6. FastAPI simula digitação:
   - POST `/chat/sendPresence` com "composing"
   - Sleep 2-15s (baseado em comprimento)
   - POST `/chat/sendPresence` com "paused"
   - POST `/message/sendText` com resposta
7. WhatsApp mostra "digitando..." → mensagem aparece

**Controle de concorrência:**
```python
user_locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

async def handle_whatsapp_message(remote_jid, text):
    async with user_locks[remote_jid]:
        # Garante processamento sequencial de mensagens do mesmo usuário
        state = user_states.get(remote_jid, {})
        result = await marketing_crm_graph.ainvoke(state)
        user_states[remote_jid] = result
```

**Cálculo de delay dinâmico (simulação de digitação humana):**
```python
def calcular_tempo_digitacao(resposta: str) -> int:
    tempo_base = random.uniform(2.0, 4.0)  # 2-4 segundos base
    tempo_caracteres = len(resposta) / 10 * 0.5  # +0.5s a cada 10 caracteres
    tempo_total = max(2.0, min(15.0, tempo_base + tempo_caracteres))  # 2-15s
    return int(tempo_total * 1000)  # ms
```

**Testes realizados:**
- ✅ Mensagem enviada do número de teste (71991186382) → respondida automaticamente
- ✅ Múltiplos números simultâneos → state isolado por remote_jid
- ✅ Concorrência: múltiplas mensagens do mesmo usuário → processadas sequencialmente
- ✅ Simulação de digitação funcional (WhatsApp mostra "digitando...")
- ✅ Fluxo completo: qualificação → budget filter → agendamento → confirmação

### 7. Tests
- ✅ Services testados manualmente (userService, clientService, authService, appointmentService)
- ✅ Controllers testados via curl (auth, users, clients)
- ✅ Agent testado via WhatsApp (fluxo completo end-to-end em produção)
- ✅ Sistema de bloqueio testado (6 testes manuais: normal, full block, unblock, morning block, afternoon block, cleanup)
- ✅ WhatsApp integration testado (webhook + simulação de digitação + concorrência)
- [ ] Testes unitários do agent (pytest) - pendente
- [ ] Testes HTTP dos endpoints de bloqueio - pendente

### 8. Admin Setup
- ✅ **Admin criado no banco:**
  - Email: `mdf.nicolas@gmail.com`
  - Senha: `612662nf`
  - Role: `admin`
  - UUID: `3c3420b3-0784-4ef9-afd2-58d2a99971ba`
  - Status: `is_active=True`

---

## ⏳ PENDENTE (Próximos Passos)

### 1. Ajustes Finos do Agent
- [ ] **Extração precisa de data/hora:** LLM parsing de "amanhã às 14h", "segunda às 10h"
- [ ] **Link Google Meet real:** Integração com Google Calendar API
- [ ] **Email de confirmação:** Template HTML + SMTP
- [ ] **Tratamento de edge cases:**
  - Agendamento duplicado (mesmo cliente)
  - Cliente muda de ideia durante qualificação
  - Horários fora do comercial (validação no datetime_collector)
- [ ] **Fine-tuning de prompts:** Tom mais objetivo, menos prolixo

### 2. Sistema de Bloqueio Administrativo (PRONTO PARA FRONTEND)
**Status:** Backend completo - 11 services implementados e testados  
**Funcionalidades:**
- ✅ `get_available_slots()` - Agent consulta horários livres (considera bloqueios)
- ✅ `block_full_day()` - Admin bloqueia dia inteiro (férias, feriados)
- ✅ `block_shift()` - Admin bloqueia turno específico (morning/afternoon)
- ✅ `unblock_date()` - Admin remove bloqueios de uma data
- [ ] `list_blocks()` - Listar bloqueios em período (para calendário do frontend)
- [ ] Endpoints HTTP testados via curl/Postman
- [ ] Interface frontend para admin gerenciar bloqueios

### 3. Frontend de Gerenciamento de Bloqueios
- [ ] Criar página de calendário para admin
- [ ] Visualizar bloqueios existentes (dia inteiro, manhã, tarde)
- [ ] Adicionar bloqueio via clique no calendário
- [ ] Remover bloqueio via botão
- [ ] Sincronizar com backend (GET /blocks, POST /blocks, DELETE /blocks)

### 4. Testes End-to-End
- [ ] Pytest para todos os nodes do agent
- [ ] Testes de integração WhatsApp → Agent → Database
- [ ] Validar com diferentes inputs (orçamentos diversos, recusas, erros)
- [ ] Testar persistência de contexto em conversas longas (múltiplas sessões)
- [ ] Stress test: múltiplos usuários simultâneos

### 5. Deploy MVP
- [ ] Docker Compose: FastAPI + PostgreSQL + Evolution API + (opcional) Redis
- [ ] Scripts de inicialização (criar admin, popular dados de teste)
- [ ] Configurar variáveis de ambiente (.env para produção)
- [ ] Documentação de uso (README com instruções de deploy)
- [ ] Monitoramento básico (logs, health checks)

---

## 📝 REGRAS E PADRÕES DO PROJETO

### Workflow Obrigatório
1. **SEMPRE** apresentar código completo → aguardar aprovação → implementar
2. **UM item por vez** (nunca batch de implementações)
3. **Testar imediatamente** após cada implementação
4. **Nunca sugerir** pular etapas (usuário decide quando avançar)

### Stack Técnica
- **Backend:** FastAPI 0.115+ (async)
- **Database:** PostgreSQL 15+ com asyncpg + SQLAlchemy 2.0 async
- **Auth:** PyJWT (⚠️ **NÃO usar python-jose**)
- **Hashing:** passlib com bcrypt
- **Tests:** pytest + pytest-asyncio + TestClient
- **Validation:** Pydantic v2
- **LLM:** Groq API (llama-3.3-70b-versatile) - gratuito com limite 30 req/min
- **Agent Framework:** LangGraph 0.2+ (multi-agent orchestration)
- **WhatsApp:** Evolution API v2 (localhost:8080) via REST API + webhooks
- **Timezone:** ZoneInfo("America/Sao_Paulo") - BRAZIL_TZ

### Estrutura de Tokens
```python
# Access Token (30 minutos)
{
  "sub": "user_id (UUID)",
  "role": "admin" ou "professional",
  "exp": timestamp
}

# Refresh Token (7 dias = 10080 minutos)
{
  "sub": "user_id (UUID)",
  "role": "admin" ou "professional",
  "exp": timestamp
}
```

### Convenções de Nomenclatura

**Schemas:**
- `{Entity}Create` - Dados para criação (ex: ClientCreate)
- `{Entity}Update` - Dados para atualização parcial (ex: ClientUpdate)
- `{Entity}Response` - Dados de resposta (ex: ClientResponse)

**Services:**
- `create_{entity}(data, db)` - Criar
- `get_{entity}(id, db)` - Buscar por ID
- `get_{entity}_by_{field}(value, db)` - Buscar por campo específico (ex: get_client_by_phone)
- `list_{entities}(db)` - Listar todos
- `update_{entity}(id, data, db)` - Atualizar
- `delete_{entity}(id, db)` - Deletar

**Routers:**
- Prefixo: `/api/v1`
- Tags descritivas: `["auth"]`, `["clients"]`, etc
- Proteção: `Depends(get_current_user)` ou `Depends(require_role("admin"))`

**Agent Nodes:**
- Nome descritivo: `{action}_{agent}` (ex: qualification_agent, schedule_agent)
- Função executora: `{node_name}_node` (ex: router_node, qualification_agent_node)
- Função de roteamento: `route_after_{node}` ou `check_{condition}` (ex: route_after_classification, check_qualification_complete)

**Testes:**
- Classes organizadas: `TestGetCurrentUser`, `TestQualificationAgent`
- Nomes descritivos: `test_login_com_credenciais_validas_retorna_tokens`
- Fixtures reutilizáveis: `client`, `admin_token`, `db_session`

### Estrutura de Arquivos
```
backend/
├── app/
│   ├── agent/ ✅
│   │   ├── graph.py (workflow com 10 nodes)
│   │   ├── state.py (MarketingCRMState)
│   │   └── nodes/ (router, conversational, qualification, budget, schedule, etc)
│   ├── api/ ✅
│   │   ├── dependencies.py
│   │   ├── authControllers.py
│   │   ├── clientsControllers.py
│   │   └── userControllers.py
│   ├── core/ ✅
│   │   ├── config.py
│   │   └── database.py
│   ├── models/ ✅ (User, Client, Appointment)
│   ├── schemas/ ✅ (4 schemas)
│   └── services/ ✅ (4 services)
├── chat_interface.py ✅ (terminal interativo para testes)
├── create_admin.py ✅
├── requirements.txt ✅
└── .env (DATABASE_URL, GROQ_API_KEY, SECRET_KEY)
```

### Dependências Importantes
```txt
# Core
fastapi>=0.115.0
uvicorn[standard]
python-dotenv

# Database
sqlalchemy[asyncio]>=2.0
asyncpg
alembic

# Validation
pydantic>=2.0
pydantic-settings

# Auth
passlib[bcrypt]
pyjwt[crypto]  # ⚠️ NÃO python-jose

# Agent & LLM
langgraph>=0.2.0
langchain-core
langchain-groq
groq

# Tests
pytest
pytest-asyncio
httpx  # Para TestClient
```

---

## 🔧 COMANDOS ÚTEIS

### Rodar Agent
```bash
# Chat interativo (terminal)
python chat_interface.py

# Comandos dentro do chat:
# - reset: limpa state e recomeça conversa
# - estado: mostra state atual (flags, dados coletados)
# - sair ou exit: encerra
```

### Rodar API
```bash
uvicorn app.main:app --reload --port 8000
```

### Criar admin
```bash
python create_admin.py
```

### Migrations
```bash
alembic revision --autogenerate -m "descrição"
alembic upgrade head
```

### Testes
## 🎯 PRÓXIMOS PASSOS IMEDIATOS

1. **Completar Sistema de Bloqueio** (próximo agora)
   - Implementar `list_blocks(start_date, end_date, db)` service
   - Testar endpoints HTTP via curl/Postman
   - Integrar `get_available_slots()` no schedule_agent do LangGraph

2. **Frontend de Gerenciamento**
   - Criar interface de calendário para admin
   - Visualizar e gerenciar bloqueios
   - Conectar com endpoints de bloqueio

3. **Ajustes Finos do Agent**
   - Melhorar extração de data/hora
   - Integrar Google Calendar
   - Implementar envio de email
   - Tratar edge cases

4. **Deploy MVP**
   - Docker Compose completo
   - Documentação de uso
## 💡 NOTAS IMPORTANTES

- **Incidente de deleção do banco:** Documentado acima. Nunca rodar testes apontando para produção.
- **Scripts de restauração:** Usar `create_all`, `alembic stamp head` e `create_admin.py` para recuperação rápida.
- **Projeto mudou de foco:** Clínica odontológica → Agência de marketing (071 Digital)
- **Models simplificados:** User, Client, Appointment (removidos Professional, Service, Availability)
- **Admin único no sistema:** mdf.nicolas@gmail.com
- **LangGraph funcionando end-to-end:** 90% completo, aguardando ajustes finos
- **Groq API:** Limite gratuito 30 req/min - implementar rate limiting no webhook
- **Evolution API escolhida:** Foco em time-to-market e manutenibilidade
- **Entry point dinâmico:** Permite conversas de múltiplas mensagens com contexto preservado
- **Budget parsing inteligente:** Detecta formatos BR ("6 mil reais", "R$ 6.000,00")
- **Segment enum:** Validação robusta de tipos de negócio (clinica_odontologica, ecommerce, etc)
- **Sistema de bloqueio:** Admin bloqueia datas/turnos manualmente → Agent respeita automaticamente via `get_available_slots()`
- **Lógica de bloqueio:** `client_id=NULL` identifica bloqueios administrativos vs agendamentos reais
- **Migrations criadas:** 2 migrations (nullable client_id + BLOCKED status enum) - sistema usa abordagem `client_id=NULL`
---

## 📞 CONTATO DO PROJETO

- **Owner:** Nicolas (mdf.nicolas@gmail.com)
- **Empresa:** 071 Digital (agência de marketing)
- **Objetivo:** MVP de sistema de agendamento via WhatsApp com LangGraph agent
- **Deadline:** Não definido (foco em qualidade e aprendizado de LangGraph)
