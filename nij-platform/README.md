# NIJ — Núcleo de Inteligência Jurídica

Sistema de análise de documentos financeiros para identificação de descontos indevidos em contracheques, faturas RMC/RCC e extratos INSS.

## Stack

| Camada | Tecnologia |
|--------|-----------|
| Backend | Python 3.12 + Django 5 + DRF + JWT |
| Banco | PostgreSQL 16 |
| Fila | Celery + Redis |
| Frontend | Next.js 14 + React 18 + TypeScript |
| Estilo | Tailwind CSS + design system customizado |
| Container | Docker + Docker Compose |
| CI/CD | GitHub Actions → GHCR → SSH deploy |

## Início rápido

```bash
# 1. Clone e configure variáveis
cp .env.example .env
# Edite .env com suas credenciais

# 2. Suba tudo
docker compose up -d

# 3. Crie o superusuário Django
docker compose exec backend python manage.py createsuperuser

# 4. Acesse
# Frontend:    http://localhost
# API Docs:    http://localhost/api/docs/
# Django Admin: http://localhost/django-admin/
```

## Desenvolvimento local

### Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate  # ou .venv\Scripts\activate no Windows
pip install -r requirements.txt
cp ../.env.example .env  # ajuste DATABASE_URL para local
python manage.py migrate
python manage.py runserver
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Worker Celery (processamento de PDFs)
```bash
cd backend
celery -A core worker -l info -Q pdf_processing
```

## Arquitetura

```
nginx (80) ──┬── /api/*  → Django (8000)
             └── /*      → Next.js (3000)

Django ──── PostgreSQL
       ──── Redis ──── Celery Worker (PDF processing)
```

## Segurança implementada

- Autenticação JWT com refresh token rotation e blacklist
- Senhas com hash bcrypt via Django
- CORS configurável por variável de ambiente
- Rate limiting via nginx
- Validação de tipo e tamanho de arquivo no upload
- Auditoria completa de ações (login, upload, CRUD usuários)
- Roles: admin / analyst / viewer
- HTTPS + HSTS em produção (configurar SSL no nginx)

## CI/CD

O pipeline `.github/workflows/ci.yml` executa:
1. Testes Django + type-check TypeScript em cada PR
2. Build e push das imagens Docker para GHCR no merge em `main`
3. Deploy automático via SSH com `docker compose pull && up`

Configure os secrets no GitHub:
- `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY`
- `NEXT_PUBLIC_API_URL`
