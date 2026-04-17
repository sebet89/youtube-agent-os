# YouTube Agent OS

Sistema em Python 3.12 para criação assistida de vídeos para YouTube, com geração de conteúdo, preparo de assets, render, revisão humana, upload privado, publicação e analytics básicos.

## Visão geral

O projeto foi desenhado para operar como um “operating system” leve para um fluxo editorial de YouTube:

- conecta um canal via OAuth 2.0 oficial do Google
- cria projetos a partir de uma ideia base
- gera briefing, roteiro, título, descrição, tags e plano de produção
- prepara assets como thumbnail, locução, legendas e trilha
- renderiza vídeo
- faz upload inicial como `private`
- exige revisão humana antes da publicação
- acompanha analytics básicos do vídeo

Hoje ele já funciona bem como MVP operacional local e está estruturado para trocar providers locais por providers reais de IA e mídia quando fizer sentido.

## Principais recursos

- `Studio` server-side para iniciar o fluxo rapidamente
- `Tela de configurações` do sistema para preencher `.env` pela interface
- `Review dashboard` com preview, aprovação, publicação e status operacional
- pipeline síncrono e assíncrono
- suporte a `FFmpeg`, `Celery`, `Redis` e `PostgreSQL`
- integração com YouTube via OAuth oficial
- arquitetura separada por `services`, `adapters`, `api`, `domain` e `db`

## Arquitetura

```text
app/
  api/          # rotas FastAPI e telas server-side
  adapters/     # integrações externas e implementação concreta dos providers
  core/         # config, segurança e infraestrutura comum
  db/           # models, session e repositories
  domain/       # enums e regras de domínio
  services/     # casos de uso da aplicação
  tasks/        # Celery e workers
alembic/        # migrations
tests/          # suíte automatizada
```

Princípios do projeto:

- domínio sem dependência direta de frameworks
- serviços pequenos e orientados a caso de uso
- adapters isolando integrações externas
- upload inicial sempre `private`
- publicação pública somente após aprovação humana
- sem credenciais hardcoded

## Stack

- Python 3.12
- FastAPI
- SQLAlchemy
- Alembic
- PostgreSQL
- Redis
- Celery
- FFmpeg
- Agno
- Google APIs / OAuth

## Fluxo do produto

1. Conectar um canal do YouTube
2. Preencher as configurações do sistema
3. Criar um projeto a partir de uma ideia base
4. Gerar conteúdo
5. Preparar assets
6. Renderizar vídeo
7. Revisar humanamente
8. Subir como `private`
9. Publicar ou agendar
10. Coletar analytics

## Interfaces

### Studio

Entrada principal do sistema:

- URL: `http://localhost:8000/api/v1/studio`
- permite:
  - escolher um canal conectado
  - criar e preparar um projeto
  - abrir a tela de configurações

### Configurações do sistema

Tela para preencher variáveis importantes sem editar o `.env` manualmente:

- URL: `http://localhost:8000/api/v1/system/settings`
- cobre:
  - dados da aplicação
  - infraestrutura
  - OAuth do YouTube
  - providers de mídia e IA

### Review dashboard

Tela de operação do projeto:

- URL: `http://localhost:8000/api/v1/review/projects/{project_id}`
- permite:
  - visualizar vídeo e thumbnail
  - ajustar metadados
  - fazer upload privado
  - aprovar ou rejeitar
  - publicar ou agendar
  - acompanhar eventos operacionais

## Como rodar localmente

### 1. Subir banco e Redis

```powershell
docker compose up db redis -d
```

### 2. Criar ambiente virtual

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -e .[dev]
```

### 3. Configurar variáveis

Copie o exemplo:

```powershell
Copy-Item .env.example .env
```

Depois preencha:

- `DATABASE_URL`
- `REDIS_URL`
- `SECRET_KEY`
- `YOUTUBE_OAUTH_CLIENT_ID`
- `YOUTUBE_OAUTH_CLIENT_SECRET`
- `YOUTUBE_OAUTH_REDIRECT_URI`

Se estiver rodando `Postgres` local via Docker Compose e a API fora do Docker, use:

```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:55432/youtube_agent_os
REDIS_URL=redis://localhost:6379/0
```

### 4. Rodar migrations

```powershell
python -m alembic upgrade head
```

### 5. Subir API

```powershell
python -m uvicorn app.main:app --reload
```

### 6. Subir worker

Em outro terminal:

```powershell
.venv\Scripts\Activate.ps1
python -m celery -A app.tasks.celery_app.celery_app worker -l info -Q pipeline
```

## Rodando com Docker

```powershell
docker compose up --build
```

Serviços:

- `api`
- `worker`
- `db`
- `redis`

## Comandos úteis

```bash
make install
make format
make lint
make typecheck
make test
make run
make run-worker
make alembic-upgrade
make docker-up
make docker-down
```

## OAuth do YouTube

O fluxo usa OAuth 2.0 oficial do Google.

Passos:

1. criar projeto no Google Cloud
2. ativar YouTube Data API v3
3. configurar a tela de consentimento OAuth
4. criar um `OAuth Client ID` do tipo `Web application`
5. cadastrar exatamente:

```text
http://localhost:8000/api/v1/oauth/youtube/callback
```

Depois, no app:

- abrir `http://localhost:8000/api/v1/oauth/youtube/authorize`
- concluir o consentimento
- validar o callback

## Providers de mídia

### Modo local e barato

Bom para desenvolvimento:

```env
THUMBNAIL_PROVIDER=deterministic
VIDEO_PROVIDER=ffmpeg
TTS_PROVIDER=edge_tts
TTS_VOICE_NAME=pt-BR-AntonioNeural
TTS_RATE=0
```

### Modo Google Cloud / Vertex AI

Quando quiser ir para geração mais moderna:

```env
GOOGLE_CLOUD_PROJECT=seu-projeto
GOOGLE_CLOUD_LOCATION=us-central1
THUMBNAIL_PROVIDER=vertex_imagen
VIDEO_PROVIDER=vertex_veo
VERTEX_IMAGEN_MODEL=imagen-4.0-fast-generate-001
VERTEX_VEO_MODEL=veo-3.0-fast-generate-001
VERTEX_VEO_ASPECT_RATIO=16:9
VERTEX_VEO_RESOLUTION=720p
VERTEX_VEO_DURATION_SECONDS=8
VERTEX_VEO_GENERATE_AUDIO=true
TTS_PROVIDER=google_cloud
GOOGLE_TTS_VOICE_NAME=pt-BR-Chirp3-HD-Achernar
GOOGLE_TTS_LANGUAGE_CODE=pt-BR
GOOGLE_TTS_SPEAKING_RATE=1.0
```

Observações:

- exige ADC configurado
- exige billing ativo no Google Cloud
- `Imagen`, `Veo` e `Google TTS` geram custo real

## Qualidade e validação

O projeto roda com:

- `ruff`
- `mypy`
- `pytest`

Última validação local desta versão:

- `57 passed`
- `mypy` sem erros
- `ruff` sem erros

## Segurança

Antes de publicar o repositório:

- não suba `.env`
- não exponha `client_secret`, `secret_key` ou tokens
- se alguma credencial foi mostrada durante testes, rotacione
- revise variáveis locais e histórico de terminal

## Status atual

O produto já entrega:

- OAuth com YouTube
- criação de projetos
- geração de conteúdo
- preparo de assets
- render
- revisão humana
- upload privado
- publicação
- agendamento
- analytics básicos
- timeline operacional
- configuração do sistema pela interface

## Próximos passos naturais

- autenticação própria de operadores
- storage externo para assets
- observabilidade mais forte
- histórico de analytics mais rico
- deploy de staging e produção
- redução de custos para providers generativos

## Licença

Defina aqui a licença desejada antes de publicar em produção ou abrir para terceiros.
