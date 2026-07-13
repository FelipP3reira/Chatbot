# Chatbot

Um chatbot com backend próprio: a resposta chega token a token, o histórico fica
guardado por conversa, e o modelo responde consultando os documentos que você
enviou (RAG). O provedor de LLM fica atrás de uma interface e é escolhido por
variável de ambiente — a chave da API nunca aparece no código.

## Stack

- **Python 3.12 + FastAPI** (async)
- **Postgres + pgvector** — histórico e índice vetorial no mesmo banco
- **Redis** — rate limit e teto de custo por conversa
- **Anthropic (Claude)** como provedor padrão, atrás de um `Protocol`
- **sentence-transformers** para os embeddings, rodando na máquina
- **Frontend** HTML + JS vanilla, sem build

## Como rodar

Pré-requisitos: Python 3.12+ e Docker.

```bash
cp .env.example .env          # preencha ANTHROPIC_API_KEY
docker compose up -d          # Postgres na 5437, Redis na 6383
python -m venv .venv && .venv/bin/pip install -e ".[dev]"
alembic upgrade head          # cria o schema e a extensão pgvector
uvicorn app.main:app --reload # a interface fica em http://localhost:8000
```

Não tem chave da Anthropic? `PROVEDOR_LLM=fake` e `EMBEDDER=hashing` sobem o
projeto inteiro offline, sem rede e sem custo.

```bash
.venv/bin/pytest              # a suíte roda contra o Postgres e o Redis do compose
```

Os testes criam e migram um banco `chatbot_teste` próprio e usam o banco 1 do
Redis, então nunca encostam nos dados de desenvolvimento. Eles aplicam as
migrações reais: uma migração que divirja dos modelos quebra a suíte.

## Configuração

| Variável | Papel |
| ----------------------------------- | ------------------------------------------------- |
| `PROVEDOR_LLM` | `anthropic` (API real) ou `fake` (sem rede) |
| `ANTHROPIC_API_KEY` | Obrigatória quando o provedor é `anthropic` |
| `MODELO_LLM` | Modelo usado nas respostas |
| `EMBEDDER` | `local` (sentence-transformers) ou `hashing` |
| `MODELO_EMBEDDING` | Modelo de embeddings quando `EMBEDDER=local` |
| `DATABASE_URL` | Postgres com a extensão pgvector |
| `REDIS_URL` | Rate limit e orçamento de tokens |
| `ORIGENS_PERMITIDAS` | Origens aceitas pelo CORS |
| `MENSAGENS_POR_MINUTO_POR_IP` | Rate limit por IP |
| `MENSAGENS_POR_MINUTO_POR_CONVERSA` | Rate limit por conversa |
| `TETO_DE_TOKENS_POR_CONVERSA` | Limite de custo por conversa |

A configuração é validada **na subida do processo**: se o provedor é `anthropic`
e a chave não está no ambiente, a aplicação não sobe. Errar cedo é melhor que
descobrir na primeira mensagem do usuário. A chave é um `SecretStr`, então não
vaza em log, `repr()` ou traceback.

## Streaming

`POST /conversas/{id}/mensagens` devolve `text/event-stream`:

```
event: pedaco
data: {"texto": "Olá"}

event: fim
data: {}
```

Se o provedor cair, chega `event: erro` com uma mensagem em português — o stream
já respondeu `200`, então não existe mais status HTTP para contar o problema. Por
isso o `404` de conversa inexistente é verificado **antes** de o stream abrir.

Os dados vão em JSON porque uma resposta com quebra de linha partiria o evento
SSE ao meio.

**SSE em vez de WebSocket:** o fluxo é unidirecional (token a token), reconecta
sozinho e não exige infraestrutura de socket. WebSocket só valeria a pena para
interromper a geração no meio.

## Resiliência do provedor

O limite de espera é **por pedaço**, não pela resposta inteira: uma resposta
longa é legítima, um provedor mudo não.

Falhas temporárias (rede, `429`, `5xx`) são repetidas com backoff exponencial e
jitter; `4xx` não, porque insistir num pedido inválido só queima cota. E se a
falha acontece **depois do primeiro pedaço**, não há retry: o usuário já leu
aquele texto, e repetir duplicaria a resposta na tela.

A troca só entra no histórico quando a resposta termina inteira — uma falha no
meio não deixa meia-resposta no banco.

## RAG

`POST /documentos` divide o texto em trechos com sobreposição (a resposta pode
estar exatamente na emenda), gera os embeddings e grava tudo no Postgres. Cada
pergunta recupera até 4 trechos por distância do cosseno (índice HNSW) e os
injeta no prompt. A busca usa **só a pergunta atual**: o histórico antigo puxaria
trechos do assunto anterior.

**Embeddings rodam na máquina.** A Anthropic não expõe API de embeddings, então o
vetor vem de outro lugar: `all-MiniLM-L6-v2` (384 dimensões), atrás de um
`Protocol`. Sem chave, sem custo, e o RAG inteiro funciona offline. Trocar por um
provedor de API é implementar a interface.

**O corte de distância foi medido, não chutado.** Comparando uma pergunta
pertinente com uma de outro assunto:

| Embedder | Pergunta pertinente | Pergunta de outro assunto |
| -------- | ------------------- | ------------------------- |
| MiniLM | 0,32 | 0,69 |
| hashing | 0,34 | 0,88 |

Um corte em **0,5** separa os dois casos. Com o `0,75` que eu tinha estimado no
começo, uma pergunta sobre Marte traria o documento sobre café para o prompt.

**pgvector em vez de FAISS:** o índice vive na mesma transação do documento e
sobrevive a um restart. FAISS é in-process e evapora junto com o processo.

## Segurança

**Trecho recuperado é dado, não instrução.** Um documento é conteúdo não
confiável — quem o envia pode escrever "ignore as instruções anteriores". Cada
trecho entra delimitado por `<trecho>`, precedido de um aviso explícito de que
aquilo não deve ser obedecido, e com as marcas de fechamento escapadas, para que
um documento envenenado não encerre o próprio bloco e escreva fora dele.

**XSS no render do chat.** A resposta do modelo pode carregar o texto de um
documento enviado por outra pessoa. Toda escrita na tela passa por `textContent`;
nada de HTML cru, nada de markdown (que é por onde HTML voltaria). Um teste falha
se as APIs de escrita de HTML aparecerem no JavaScript. Como segunda camada, a
CSP recusa `unsafe-inline`: um `<script>` que escapasse simplesmente não roda.

**Limites de uso e custo.** Dois rate limits, porque protegem de coisas
diferentes: o **por IP** contém quem abre conversas novas em série; o **por
conversa** contém quem martela uma só. Os dois usam janela deslizante — a janela
fixa zera na virada do minuto e deixa passar o dobro num intervalo curto.

O **teto de tokens por conversa** é reservado *antes* de chamar o modelo, porque
depois já custou. A resposta gerada é sempre contabilizada, mesmo estourando o
teto: ela não pode ser "desgerada" — quem paga é a pergunta seguinte, que será
barrada. Reserva e contagem rodam em **Lua**, num comando só: ler e somar em dois
passos deixaria duas requisições simultâneas passarem pelo teto ao mesmo tempo.

**Demais itens.** `X-Forwarded-For` é ignorado (é escrito pelo cliente, e sem um
proxy que garanta a sobrescrita qualquer um forjaria o próprio IP); toda entrada
é validada e tem teto de tamanho; as queries são parametrizadas, inclusive a
busca vetorial; o `500` engole o traceback no log e devolve mensagem humana.

## Trade-offs conhecidos

- **A contagem de tokens é uma estimativa** (`caracteres / 4`), não a cobrança do
  provedor. Serve para barrar uma sessão cara antes de a conta chegar, e erra
  para mais em português — o lado seguro de errar. A contagem exata exigiria uma
  chamada extra à API a cada mensagem.
- **A janela de histórico corta pelas mensagens mais antigas**, sem resumir o que
  saiu. Um resumo custaria uma chamada ao modelo por troca.
- **O rate limit atende um deploy**, não vários datacenters — isso exigiria
  coordenação entre instâncias de Redis.
- **O embedder de hashing não entende sinônimos.** Ele existe para os testes e
  para rodar sem download — em produção, `EMBEDDER=local`.

## Estrutura

```
app/
  config.py       env validado na subida
  erros.py        resposta de erro única: {erro: {codigo, mensagem, detalhes}}
  seguranca.py    CSP e demais cabeçalhos
  api/            rotas HTTP
  llm/            interface do provedor, Anthropic, fake e resiliência
  rag/            chunker, embeddings, índice e montagem do contexto
  conversa/       histórico persistido e serviço de conversa
  limites/        rate limit e orçamento de tokens
web/              frontend sem build
migracoes/        Alembic
tests/            integração contra Postgres e Redis
```
