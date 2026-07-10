# Chatbot

Um chatbot com backend próprio: streaming da resposta, histórico persistido por
sessão e RAG (busca nos seus documentos antes de responder). O provedor de LLM
fica atrás de uma interface e é escolhido por variável de ambiente — a chave da
API nunca aparece no código.

## Stack

- **Python + FastAPI** (async)
- **Postgres + pgvector** — histórico e índice vetorial no mesmo banco
- **Redis** — rate limit e controle de custo por sessão
- **Anthropic (Claude)** como provedor padrão, atrás de um `Protocol`
- **Frontend** HTML + JS vanilla, sem build

## Como rodar

Pré-requisitos: Python 3.12+ e Docker.

```bash
cp .env.example .env          # preencha ANTHROPIC_API_KEY
docker compose up -d          # Postgres na 5437, Redis na 6383
python -m venv .venv && .venv/bin/pip install -e ".[dev]"
alembic upgrade head          # cria o schema
.venv/bin/pytest              # a suíte roda com o provedor "fake", sem rede
uvicorn app.main:app --reload
```

Sem chave da Anthropic? Use `PROVEDOR_LLM=fake` e o projeto sobe inteiro offline.

Os testes exigem o Docker de pé: criam e migram um banco `chatbot_teste`
próprio, aplicando as migrações reais — se uma migração divergir dos modelos, a
suíte quebra.

## Configuração

| Variável | Papel |
| ---------------- | -------------------------------------------------------------- |
| `PROVEDOR_LLM` | `anthropic` (API real) ou `fake` (sem rede) |
| `ANTHROPIC_API_KEY` | Obrigatória quando o provedor é `anthropic`. Só em ambiente. |
| `MODELO_LLM` | Modelo usado nas respostas |
| `DATABASE_URL` | Postgres com a extensão pgvector |
| `REDIS_URL` | Rate limit e orçamento de tokens |
| `ORIGENS_PERMITIDAS` | Lista de origens aceitas pelo CORS |

A configuração é validada **na subida do processo**: se o provedor é `anthropic`
e a chave não está no ambiente, a aplicação não sobe. Errar cedo é melhor que
descobrir na primeira mensagem do usuário. A chave é um `SecretStr`, então não
vaza em log, `repr()` ou traceback.

## Estrutura

```
app/
  config.py       env validado
  erros.py        resposta de erro única: {erro: {codigo, mensagem, detalhes}}
  api/            rotas HTTP
  llm/            interface do provedor + implementações
  rag/            ingestão, embeddings, busca, montagem de contexto
  conversa/       histórico persistido
  limites/        rate limit e orçamento de tokens
web/              frontend
tests/            testes de integração
```

## Estado

Em construção, por fatias:

- [x] Bootstrap: configuração validada, tratamento central de erro, saúde, Docker
- [x] Conversa persistida, histórico com janela e provedores (Anthropic e fake)
- [ ] Streaming (SSE) e resiliência do provedor: timeout, retry e fallback
- [ ] RAG: ingestão, embeddings, busca por similaridade, injeção de contexto
- [ ] Rate limit e limite de tokens por sessão
- [ ] Frontend com sanitização
