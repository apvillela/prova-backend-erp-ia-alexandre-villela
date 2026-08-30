# Timeline

Prazo da prova: 72h a partir do recebimento. Registro do que foi feito e quando.

## 28/08

| Hora | O quê |
| --- | --- |
| 00:49 | `docs: add readme.md` — README inicial na `main` com objetivo e stack escolhida |
| 01:26 | `docs: add template structure to readme` — seção de estrutura de pastas |
| 01:35 | `feat: init template` na `initial-branch` — template da API (54 arquivos) |
| 19:07 | `chore: add pull request template` |
| 19:0x | Stack subiu no Docker: app, postgres, redis e migrate, com health check respondendo |

## Decisões tomadas

| Decisão | Motivo |
| --- | --- |
| Python 3.11 | versão estável, todas as libs do ecossistema suportam |
| Estrutura no padrão do `template-microservice` interno | `services/<dominio>/{router,controller,schemas}`, cada domínio isolado numa pasta |
| Pydantic v2 + pydantic-settings | v2 é o padrão atual; o template interno ainda usa v1 |
| SQLAlchemy async + asyncpg | não bloquear o event loop do FastAPI |
| Alembic | schema versionado; `create_all()` não altera tabela existente |
| arq para fila | async-native, usa o Redis que já existe |
| uv + `uv.lock` | lock reproduzível e build rápido no Docker |
| Migration em container próprio (`migrate`) | com N réplicas, migrar no `lifespan` faria todas correrem juntas |
| Request-id + access log próprios | as libs internas de log/observabilidade são privadas |
| Sem lib proprietária | repositório precisa buildar fora da rede da empresa |

## Próximos passos

- [ ] Parte 3: CRUD de Produtos/Estoque com JWT, paginação, filtros e cache
- [ ] Parte 2: endpoint consolidado com `asyncio.gather`, timeout, retry e degradação parcial
- [ ] Parte 5: agente determinístico de consulta em linguagem natural
- [ ] Partes 1, 6 e 7: respostas teóricas no README
- [ ] Seção "Uso de IA" no README
