# AGENTS.md

## 1. Visao Geral Do Produto

Este repositorio implementa um agente de IA para YouTube.

Objetivo do sistema:
- receber uma ideia de video;
- gerar roteiro;
- gerar titulo, descricao, tags e prompt de thumbnail;
- gerar assets de midia por meio de adapters;
- montar o video final;
- subir o video para o YouTube pela API oficial;
- salvar historico, jobs, runs e metricas operacionais.

Stack principal:
- Python 3.12
- FastAPI
- Agno
- PostgreSQL
- SQLAlchemy
- Alembic
- Redis
- Celery
- FFmpeg
- Playwright

Principios do produto:
- modularidade desde o inicio;
- baixo acoplamento entre dominio e providers externos;
- tipagem e testabilidade como requisitos de projeto;
- rastreabilidade de jobs, execucoes e metricas;
- seguranca por padrao;
- publicacao com controle humano antes de expor videos como `public`.

Regras de negocio obrigatorias:
- a autenticacao do YouTube deve usar OAuth 2.0;
- nunca usar login/senha direta do Google no codigo;
- uploads devem sair inicialmente como `private` por padrao;
- deve existir human-in-the-loop antes de qualquer publicacao em `public`.

## 2. Convencoes De Arquitetura

Diretrizes gerais:
- organizar o codigo em camadas explicitas: `api`, `application`, `domain`, `infrastructure`, `workers`;
- manter o dominio independente de frameworks, ORMs, SDKs e providers de IA;
- usar interfaces/protocols/ports para tudo que depende de servicos externos;
- implementar integracoes externas em adapters na camada de infraestrutura;
- manter regras de orquestracao na camada de aplicacao;
- expor HTTP com FastAPI apenas como borda do sistema;
- executar tarefas assincronas e longas via Celery;
- usar Redis para fila, coordenacao e cache quando fizer sentido;
- usar FFmpeg e Playwright por adapters/servicos dedicados, nunca espalhados pelo dominio.

Arquitetura recomendada:
- `domain/`: entidades, value objects, regras de negocio, contratos;
- `application/`: casos de uso, servicos de orquestracao, DTOs, validacoes de fluxo;
- `infrastructure/`: adapters de IA, YouTube, banco, storage, FFmpeg, Playwright, filas;
- `api/`: rotas FastAPI, schemas de entrada/saida, dependencia de autenticacao;
- `workers/`: jobs Celery e pipelines assincronos;
- `tests/`: testes unitarios, integracao e fluxos criticos.

Regras obrigatorias:
- sempre planejar antes de implementar features grandes;
- nunca acoplar provider de IA diretamente ao dominio; usar adapters/interfaces;
- manter cada modulo com responsabilidade clara e fronteiras bem definidas;
- evitar funcoes ou servicos "god object" que concentram multiplas responsabilidades;
- eventos, jobs e runs devem ter identificadores rastreaveis;
- toda integracao externa deve ter tratamento de erro, timeout, retry e logs estruturados.

Planejamento de features grandes:
- descrever objetivo, escopo e limites;
- listar impactos em dominio, API, workers, banco e integracoes;
- definir estrategia de rollout;
- identificar testes necessarios;
- validar riscos de seguranca e operacao antes de codificar.

## 3. Convencoes De Codigo Python

Padroes gerais:
- usar Python 3.12;
- escrever codigo tipado com type hints;
- preferir funcoes e classes pequenas, coesas e testaveis;
- documentar decisoes nao obvias com comentarios curtos e objetivos;
- evitar logica de negocio em controllers, modelos ORM ou tasks sem encapsulamento.

Convencoes praticas:
- seguir PEP 8 e manter formatacao automatica;
- usar nomes descritivos e orientados ao dominio;
- preferir `pathlib` a strings de caminho quando aplicavel;
- preferir `Enum`, `dataclass` e `Protocol` quando ajudarem a explicitar contrato;
- separar schemas de API, modelos de dominio e modelos ORM;
- nao reutilizar diretamente modelos ORM como contrato externo;
- retornar erros de forma previsivel e observavel;
- usar configuracao via variaveis de ambiente e objetos de settings.

Assinaturas e contratos:
- toda funcao publica relevante deve ter tipos de entrada e saida;
- interfaces de adapters devem explicitar comportamento esperado, erros e limites;
- codigo novo deve ser pensado para mock/fake em testes.

## 4. Regras Para Seguranca

Regras obrigatorias:
- nunca usar credenciais hardcoded;
- nunca commitar segredos, tokens, cookies, arquivos OAuth sensiveis ou dumps reais;
- YouTube deve autenticar somente via OAuth 2.0;
- nunca implementar login/senha direta do Google;
- upload deve ser `private` por padrao;
- qualquer transicao para `public` deve exigir aprovacao humana explicita;
- principio do menor privilegio para tokens, contas de servico e acessos internos;
- mascarar segredos em logs, traces e mensagens de erro.

Praticas de seguranca:
- carregar segredos apenas por variaveis de ambiente, secret manager ou cofre equivalente;
- validar e sanitizar entradas externas;
- definir timeouts e retries com limites para chamadas externas;
- registrar auditoria de acoes sensiveis, especialmente autenticacao, upload e publicacao;
- revisar escopos OAuth necessarios e evitar permissoes excessivas;
- proteger endpoints administrativos e operacionais;
- evitar armazenar tokens em texto puro quando houver alternativa segura;
- revisar dependencias e versoes com foco em vulnerabilidades conhecidas.

## 5. Regras Para Migrations E Banco

Diretrizes:
- usar PostgreSQL como banco principal;
- acesso ao banco deve passar por SQLAlchemy;
- schema evolui exclusivamente por Alembic;
- nunca alterar schema manualmente em producao sem migration versionada;
- toda mudanca de modelo persistido deve vir acompanhada de migration correspondente.

Boas praticas:
- migrations devem ser pequenas, revisaveis e reversiveis quando possivel;
- nomear tabelas, colunas, indices e constraints de forma consistente;
- explicitar constraints importantes no banco, nao apenas na aplicacao;
- adicionar indices para consultas criticas e fluxos operacionais relevantes;
- considerar impacto de locks, backfills e volume de dados antes de alterar tabelas grandes;
- separar claramente entidades de historico, jobs, runs e metricas quando o ciclo de vida for diferente.

Dados e rastreabilidade:
- persistir historico de execucoes, jobs e runs com timestamps e status;
- modelar metricas e eventos com foco em auditoria e observabilidade;
- evitar apagar dados operacionais sem politica explicita de retencao.

## 6. Regras Para Testes

Regras obrigatorias:
- sempre criar ou atualizar testes ao alterar comportamento;
- nenhuma mudanca de feature ou regra de negocio deve sair sem cobertura adequada;
- bugs corrigidos devem ganhar teste de regressao sempre que viavel.

Estrategia de testes:
- priorizar testes unitarios para dominio e casos de uso;
- usar testes de integracao para banco, fila, adapters e API;
- cobrir fluxos criticos ponta a ponta quando houver risco operacional;
- mockar providers externos de forma controlada;
- usar fakes/adapters de teste para IA, YouTube, FFmpeg e Playwright sempre que possivel.

Fluxos minimos a cobrir:
- criacao de ideia de video e disparo de pipeline;
- geracao de roteiro e metadados;
- persistencia de jobs, runs e historico;
- upload para YouTube com status inicial `private`;
- bloqueio de publicacao `public` sem aprovacao humana;
- falhas e retries em integracoes externas.

## 7. Comandos Principais De Desenvolvimento

Ajuste os comandos conforme a estrutura real do repositorio, mas preserve estes padroes:

```bash
# criar ambiente virtual
python -m venv .venv

# ativar ambiente virtual (Linux/macOS)
source .venv/bin/activate

# ativar ambiente virtual (Windows PowerShell)
.venv\Scripts\Activate.ps1

# instalar dependencias
pip install -U pip
pip install -r requirements.txt

# subir API localmente
uvicorn app.main:app --reload

# rodar worker Celery
celery -A app.workers.celery_app worker -l info

# rodar migrations
alembic upgrade head

# criar nova migration
alembic revision --autogenerate -m "describe_change"

# rodar testes
pytest

# rodar testes com cobertura
pytest --cov=app --cov-report=term-missing
```

Se o projeto adotar `src/`, `pyproject.toml`, `Makefile` ou outro layout, manter o `AGENTS.md` atualizado com os comandos reais.

## 8. Checklist De PR/Review

Antes de abrir ou aprovar PR, verificar:
- o objetivo da mudanca esta claro;
- houve planejamento previo se a feature e grande;
- a arquitetura respeita separacao entre dominio, aplicacao e infraestrutura;
- nenhum provider de IA foi acoplado diretamente ao dominio;
- nao existem credenciais hardcoded;
- YouTube OAuth 2.0 continua sendo o unico fluxo de autenticacao suportado;
- upload continua saindo como `private` por padrao;
- a exigencia de human-in-the-loop para publicacao `public` foi preservada;
- migrations foram criadas e revisadas quando houve mudanca de persistencia;
- testes foram criados ou atualizados;
- logs, metricas e tratamento de erro foram considerados;
- tipos e contratos foram mantidos consistentes;
- documentacao, exemplos e comandos locais continuam corretos.

## Regras Obrigatorias Consolidadas

- sempre planejar antes de implementar features grandes;
- sempre criar ou atualizar testes ao alterar comportamento;
- nunca acoplar provider de IA diretamente ao dominio; usar adapters/interfaces;
- nunca usar credenciais hardcoded;
- nunca usar login/senha direta do Google no codigo;
- sempre usar OAuth 2.0 para integracao com YouTube;
- sempre iniciar uploads como `private`;
- sempre exigir aprovacao humana antes de publicar como `public`.
