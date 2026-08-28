## Tudo está sujeito a mudanças.

API do módulo de Produtos e Estoque de um ERP.
O serviço expõe o CRUD do domínio, consulta outros módulos (financeiro, clientes)
e vai responder perguntas em linguagem natural sobre os dados.
## Stack

- **Python 3.11** por motivos de: versão estável e amplamente suportada pelas libs do ecossistema
- **FastAPI** padrão pra APIS simples e robustas
- **Pydantic** imprescindível pra validação de dados, entrada, saída, contratos de API
- **PostgreSQL** + **SQLAlchemy** (async) — persistência
- **Redis**  cache de leitura e fila do worker de background
- **Docker / Docker Compose** uniformidade e facilidade de deploy,

Ainda em construção

## Estrutura

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
