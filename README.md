## Tudo está sujeito a mudanças.

API do módulo de Produtos e Estoque de um ERP.
O serviço expõe o CRUD do domínio, consulta outros módulos (financeiro, clientes)
e vai responder perguntas em linguagem natural sobre os dados.

## Instrução de execução

```bash
docker compose up --build
```

Funciona sem configuração: os containers usam o `.env.example` como base. Para customizar (portas, senhas, `JWT_SECRET`), crie um `.env` — ele sobrescreve o example.

O compose sobe Postgres, Redis, as migrações (Alembic, em container próprio antes da API), a API, o worker (arq) e o frontend.

- Frontend: http://localhost:3000 (configurável via `FRONTEND_PORT`)
- API: http://localhost:8000 — Swagger em http://localhost:8000/docs
- Login padrão: `lidertecnica` / `password123!` (do `.env.example`)

## Respostas das questões teóricas

### Questão 1


## Uso de IA


## Extras

- **Rate limit**: `POST /alertas/estoque-baixo/verificar` aceita 3 chamadas por minuto por usuário (contador INCR+EXPIRE no Redis, fail-open se o Redis cair). Estourou, responde `429` com header `Retry-After`. Configurável via `RATE_LIMIT_VERIFICAR_MAX` e `RATE_LIMIT_VERIFICAR_JANELA`.
- **Ordenação**: `GET /produtos` aceita `ordenar_por` (`nome` | `quantidade_em_estoque` | `data_atualizacao`) e `ordem` (`asc` | `desc`), resolvidos com `ORDER BY` no banco. No front, os cabeçalhos da tabela são clicáveis.
- **Por baixo dos panos**: cada tela do front tem um painel expansível explicando o fluxo real por trás dela (fila, cache, gather, etc.).

## Links do Portfólio
