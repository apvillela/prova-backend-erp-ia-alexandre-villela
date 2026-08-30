# Notas

Rascunho do que penso com o intuito de escrever o que penso e como penso

## Em aberto

- `/health_check` retorna `dict[str, str]`, então o Swagger mostra `additionalProp1/2/3` no example. Trocar por um schema Pydantic (`HealthCheck`) resolve — o template interno tem o mesmo comportamento.
- `/metrics` do Prometheus ficou de fora do template. São ~3 linhas com `prometheus-fastapi-instrumentator`, e a Questão 1 pede pra citar ferramentas de observabilidade.
- Kong não entra no repositório: a Questão 1 é teórica. Se sobrar tempo, um Kong DB-less no compose deixaria a resposta demonstrável.
- Serviço `worker` do arq ainda não está no compose — entra junto com a primeira task da fila.
- JWT: `pyjwt` e `bcrypt` já estão nas dependências, sem código ainda. Entra com a Parte 3.

## Ambiente local

- Postgres do compose está mapeado em `127.0.0.1:5433` porque a 5432 já está ocupada por um Postgres da máquina.
- `.env` local não define `POSTGRES_HOST`/`REDIS_HOST`: dentro do compose valem os defaults do `config.py`, que são os nomes dos serviços.
- Build precisa do `docker-buildx-plugin` (o Dockerfile usa `RUN --mount`, que só existe no BuildKit).

## Perguntas da prova que ainda quero responder melhor

- Parte 1: como justificar a divisão dos microsserviços sem cair em "um serviço por tabela".
- Parte 5 Q9: onde exatamente o servidor MCP se encaixa na arquitetura desenhada na Parte 1.
- Parte 6: resposta sobre Go — concordar sem parecer bajulação, e mostrar plano de aprendizado concreto.

## Stack (saiu do README)

- **Python 3.11** por motivos de: versão estável e amplamente suportada pelas libs do ecossistema
- **FastAPI** padrão pra APIS simples e robustas
- **Pydantic** imprescindível pra validação de dados, entrada, saída, contratos de API
- **PostgreSQL** + **SQLAlchemy** (async) — persistência
- **Redis**  cache de leitura e fila do worker de background
- **Docker / Docker Compose** uniformidade e facilidade de deploy,

Ainda em construção

## Estrutura (saiu do README)

```
bin/run.py                 sobe a api com uvicorn
src/erp_api/
  config.py                settings lidas do .env
  main.py                  app fastapi, middlewares e handlers
  api.py                   junta os routers
  lifespan.py              checa postgres e redis no start
  logging_config/          log no console e em arquivo
  middlewares/             request id e access log
  exceptions/              erros de domínio e handlers http
  database/                engine, sessão e base dos models
  caching/                 cliente redis
  services/<dominio>/      router, controller e schemas de cada domínio
migrations/                alembic
tests/                     testes unitários
scripts/                   lint, format, test e build da imagem
```

- domínio novo é uma pasta em `services/`, com router, controller e schemas próprios
- router cuida só de http, controller tem a regra, database isola o sqlalchemy
- erro de domínio sobe como exceção e o handler traduz em status code, então o controller não conhece http
- toda resposta de erro sai como `{"detail": [{"msg": "..."}]}`
- por enquanto só o health check está implementado: `/health_check` e `/health/readiness`
