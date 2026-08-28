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