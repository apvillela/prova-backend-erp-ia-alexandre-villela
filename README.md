## Tudo está sujeito a mudanças.

API do módulo de Produtos e Estoque de um ERP.
O serviço expõe o CRUD do domínio, consulta outros módulos (financeiro, clientes)
e vai responder perguntas em linguagem natural sobre os dados.

## Instrução de execução

```bash
docker compose up --build
```

Roda sem `.env`: os containers usam o `.env.example` como base. Um `.env` local sobrescreve o que precisar (portas, senhas, `JWT_SECRET`).

O compose sobe Postgres, Redis, as migrações (Alembic, em container próprio antes da API), a API, o worker (arq) e o frontend.

- Frontend: http://localhost:3000 (configurável via `FRONTEND_PORT`)
- API: http://localhost:8000 — Swagger em http://localhost:8000/docs
- Login padrão: `lidertecnica` / `password123!` (do `.env.example`)

## Respostas das questões teóricas

### Questão 1


## Uso de IA


## Extras

- Rate limit: `POST /alertas/estoque-baixo/verificar` aceita 3 chamadas por minuto por usuário (INCR+EXPIRE no Redis, fail-open se o Redis cair). Acima disso responde `429` com `Retry-After`. Ajustável via `RATE_LIMIT_VERIFICAR_MAX` e `RATE_LIMIT_VERIFICAR_JANELA`.
- Ordenação: `GET /produtos` aceita `ordenar_por` (`nome`, `quantidade_em_estoque`, `data_atualizacao`) e `ordem` (`asc`/`desc`), resolvidos com `ORDER BY` no banco. No front, os cabeçalhos da tabela são clicáveis.
- Cada tela do front tem um painel "por baixo dos panos" explicando o fluxo real por trás dela.

## Links do Portfólio
