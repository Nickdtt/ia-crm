# Scripts Utilitários

Scripts administrativos e de setup para o projeto.

## 📝 Scripts Disponíveis

### `create_admin.py`
Cria usuário admin no banco de dados Supabase.

```bash
python scripts/create_admin.py
```

**Credenciais criadas:**
- Email: `mdf.nicolas@gmail.com`
- Senha: `612662nf`
- Role: admin

### `check_models.py`
Verifica modelos disponíveis na API do Google Gemini.

```bash
python scripts/check_models.py
```

Lista todos os modelos com suporte a `generateContent`.

## 🔧 Como usar

Todos os scripts devem ser executados a partir da raiz do backend:

```bash
cd backend
python scripts/<nome_do_script>.py
```
