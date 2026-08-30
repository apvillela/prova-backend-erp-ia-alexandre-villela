## ERP - Módulo de Produtos e Estoque

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

As migrações rodam sozinhas no `docker compose up` (o container `migrate` executa `alembic upgrade head` antes da API subir). Pra popular o banco com dados de exemplo, rode o seed depois que a stack estiver de pé:

```bash
docker compose run --rm app-1 python bin/seed.py
```

O seed é idempotente: insere 10 produtos de exemplo (com casos úteis pra demo, como estoque zerado e estoque baixo) e não faz nada se o banco já tiver produto.

## Stack e decisões

- **Python 3.11** — versão estável e amplamente suportada pelas libs do ecossistema.
- **FastAPI** — padrão pra API assíncrona: validação integrada com Pydantic, OpenAPI/Swagger de graça e injeção de dependências que simplifica auth e sessão de banco.
- **Pydantic v2 + pydantic-settings** — contrato de entrada/saída da API e settings tipadas lidas do `.env`; v2 é o padrão atual.
- **SQLAlchemy 2 async + asyncpg** — ORM pelo modelo declarativo no CRUD; async pra não bloquear o event loop do FastAPI.
- **Alembic** — schema versionado e migração reproduzível; `create_all()` não altera tabela existente.
- **Redis** — cache de leitura, fila do worker e rate limit, um serviço só pra três papéis.
- **arq** — fila async-native que usa o Redis que já existe; Celery seria peso demais pra um worker.
- **uv + `uv.lock`** — lock reproduzível e build rápido no Docker.
- **Docker / Docker Compose** — a stack inteira sobe com um comando, igual em qualquer máquina.

## Respostas das questões teóricas

### Questão 1 — Arquitetura do módulo de Pedidos e Estoque

Dividiria por capacidade de negócio, não por tabela. Pedido e estoque mudam juntos (criar pedido baixa estoque, cancelar devolve), então ficam no mesmo serviço: um serviço de **Pedidos e Estoque**, dono das próprias tabelas, conversando com **Financeiro** e **Clientes**. Cada serviço com seu banco, ninguém lê tabela dos outros. Separar pedido de estoque só transformaria uma transação local numa saga distribuída sem necessidade. É o recorte deste repositório, que trata financeiro e clientes como serviços externos.

Comunicação: REST síncrono quando a resposta é necessária pra concluir a requisição (consultar limite de crédito antes de aprovar o pedido), fila quando não é ("pedido aprovado, financeiro fatura" vira evento e o financeiro consome no ritmo dele). No síncrono, o cuidado é não herdar a latência dos outros: o `/resumo` deste repo consulta as três fontes em paralelo com `asyncio.gather`, cada uma com timeout e retry com backoff (sem retry pra 4xx não transitório), e a falha de uma fonte degrada só aquele campo.

PostgreSQL é a fonte de verdade, um banco por serviço, com migração versionada. Aqui o Alembic roda num container próprio antes da API porque N réplicas migrando no startup disputariam o mesmo lock. Redis entra como cache de leitura (invalidação por versão de namespace), fila do worker `arq`, rate limit (INCR+EXPIRE) e, se precisar, pub/sub e lock distribuído. Regra: tudo que está no Redis pode sumir — cache e rate limit aqui são fail-open, se o Redis cair a API responde direto do Postgres.

O API Gateway (Kong, por exemplo) é o único ponto de entrada externo: TLS, autenticação, rate limit global e roteamento num lugar só, serviços em rede interna. Comunicação interna entre serviços não passa por ele.

Observabilidade: logs estruturados com request-id propagado (a API já gera por middleware, é o que permite seguir uma requisição que atravessou três serviços), métricas com Prometheus + Grafana (a API já expõe `/metrics`) e tracing com OpenTelemetry quando a pergunta vira em qual serviço a requisição gastou o tempo. Num ERP, monitoraria primeiro: taxa de erro e p95/p99 dos fluxos que envolvem dinheiro, profundidade e idade da fila, e divergência de estoque.

### Questão 2 — Estrutura de pastas de um serviço FastAPI

É a estrutura deste repositório: um núcleo transversal (`config.py`, `database/`, `caching/`, `middlewares/`, `exceptions/`, `logging_config/`) e um diretório `services/` onde cada domínio é uma pasta com `router.py`, `controller.py`, `schemas.py` e `models.py` — aqui: `produtos`, `alertas`, `resumo`, `agente`, `auth`, `health`.

O router cuida só de HTTP e delega. O controller tem a regra de negócio e não conhece HTTP: erro de domínio sobe como exceção e um handler central traduz em status code, então o mesmo controller serve pra endpoint, worker ou teste. Os schemas Pydantic são o contrato de entrada/saída e concentram a validação (preço negativo, nome vazio), e os models ficam na camada de banco. Não criei `repositories/` porque neste porte seria só repasse; se as queries começarem a se repetir entre controllers, a camada entra.

Testabilidade: os testes unitários exercitam schemas e controllers sem subir HTTP, e os de integração batem nos endpoints. Manutenção: domínio novo é uma pasta nova em `services/`, sem tocar nas outras. No fundo é separação de camadas no espírito de Clean Architecture, aplicando só o que se paga neste tamanho de serviço.

### Questão 3 — asyncio vs threading vs multiprocessing

`asyncio` é concorrência cooperativa numa thread só: o event loop alterna entre tarefas nos pontos de `await`, ideal quando o gargalo é esperar I/O. É a base deste projeto (FastAPI + SQLAlchemy async + asyncpg), e o exemplo é o `/resumo`: estoque, financeiro e cliente consultados ao mesmo tempo com `asyncio.gather`, pagando o tempo da fonte mais lenta em vez da soma.

`threading` também é pra I/O, mas com threads do sistema operacional. Pelo GIL só uma executa bytecode Python por vez, então não acelera conta pesada; serve pra código bloqueante que não tem versão async (lib síncrona de SFTP, driver legado). No ERP: baixar retorno bancário (CNAB) de três bancos em paralelo com uma lib que só existe síncrona, cada download numa thread ou `run_in_executor`.

`multiprocessing` é pra CPU: processos separados, cada um com seu interpretador e seu GIL, usando os núcleos de verdade, ao custo de serializar dados entre eles. No ERP: gerar o relatório mensal em PDF ou reprocessar um CSV de milhões de linhas, quebrado em pedaços por processo. Num serviço web eu nem uso direto na API: tarefa pesada vai pra fila (aqui o worker `arq`) e quem escala são os workers.

### Questão 9 — Design plugável pra um LLM real

A Parte 5 já foi implementada com essa pergunta em mente, então boa parte da resposta é o que está em `services/agente/`. As ferramentas vivem num registry (`ferramentas.py`) onde cada uma declara nome, descrição e schema de parâmetros, no mesmo formato de function calling dos provedores. O interpretador (`interprete.py`) é determinístico, por regras, e devolve uma `ChamadaFerramenta` com nome, parâmetros e confiança — o mesmo contrato que um LLM devolveria. Plugar um modelo real é trocar só essa camada, e foi o que fiz em `interprete_llm.py`: com `AGENTE_LLM_URL` apontando pra um Ollama local (profile `llm` do compose), o agente manda a pergunta e o spec das ferramentas pro modelo e recebe a mesma `ChamadaFerramenta`; se o modelo cair, demorar ou responder ferramenta fora do registry, degrada pras regras. Router, executor e validação não mudam — o campo `interprete` da resposta mostra qual caminho interpretou.

MCP: usaria, porque expõe as mesmas ferramentas pra N agentes sem N integrações. O servidor MCP é uma fachada fina, sem regra de negócio nem acesso a banco: implementei em `bin/mcp_server.py`, e cada tool chama a API REST com o mesmo login JWT de um cliente qualquer — o agente não ganha atalho pro banco, então autorização, rate limit e auditoria continuam valendo pra ele. Na arquitetura da Parte 1 ele fica ao lado do gateway, consumindo os serviços donos dos dados pela borda. O registry do agente virou a lista de tools quase um pra um.

Guardrails: o agente só tem ferramentas de leitura, e manteria isso — tool que muda estado (criar pedido, ajustar estoque) exigiria confirmação explícita do usuário antes de executar. Parâmetros sempre validados por schema antes de tocar o banco: parâmetro alucinado vira 422, não query errada. O agente só executa ferramentas do registry, nunca SQL arbitrário, e as queries têm `LIMIT` embutido. Confiança abaixo de um piso, ou pergunta não reconhecida, vira "não entendi, reformule" com as capacidades listadas.

Com LLM de verdade: logar prompt, resposta, ferramenta, tokens e latência amarrados ao request-id que já atravessa a aplicação; cache de respostas no Redis com a mesma invalidação por versão das listagens; e tratar o provedor como o `/resumo` trata fonte externa — timeout, retry com backoff pra erro transitório e fallback pro interpretador por regras quando estiver fora.

### Questão 10 — Frente em Go

Ficaria tranquilo: já tenho um leve background em Go e pro cenário descrito acho uma escolha boa mesmo. Concorrência barata com goroutines, GC de pausas curtas e binário estático que simplifica o deploy. Python com asyncio me atende bem em API de negócio — este repo é a prova — mas num pipeline de eventos de altíssimo volume o overhead do interpretador e o GIL viram teto.

Se eu discordasse, argumentaria com número, não com preferência: um protótipo pequeno nas duas linguagens medindo throughput e p99 com carga realista, mais o custo de manter uma segunda linguagem no stack (CI, libs internas, on-call). Se desse empate, defenderia ficar em Python pela homogeneidade.

Pra rampar: tenho o contato do Elton Minetto, referência em Go no Brasil, e pediria ajuda a ele pra me indicar o caminho e revisar as primeiras coisas que eu escrevesse — review de quem já escreve Go é onde se aprende a não fazer "Python com sintaxe de Go". Começaria por um componente pequeno e de baixo risco em produção (um consumer de fila bem testado) antes de qualquer serviço crítico, e mediria performance desde o início, já que essa é a promessa da frente.

## Uso de IA

Utilizei IA do início ao fim do processo, como ferramenta de desenvolvimento — as decisões são minhas. Como a prova é uma tarefa tecnicamente já resolvida, o meu trabalho foi a arquitetura e o system design: a escolha das libs (SQLAlchemy async, arq em vez de Celery, uv), o desenho do sistema de fila, se o retry do `/resumo` teria backoff exponencial e quais retornos valiam nova tentativa (a classificação de erros retentáveis — 408/425/429/5xx sim, demais 4xx não — saiu dessas decisões), a estratégia de invalidação de cache por versão de namespace, o rate limit fail-open. A partir dessas decisões a IA gerou boa parte do código, e eu revisei toda decisão importante e a maior parte dos módulos antes de commitar.

No front-end usei IA para o desenvolvimento, com feedback visual meu a cada iteração e ajustes com base no que seria a melhor experiência dentro do tempo que tive.

As mecânicas de teste e a pipeline de CI eu montei junto com a primeira versão do template, justamente pra garantir que nada gerado dali em diante entrasse quebrando: todo commit passa por lint, type check e pelos testes de regressão que fui adicionando a cada parte (schemas, retry do resumo, cache, interpretador do agente). A IA também me serviu de memória de consulta pra relembrar trechos de O Programador Pragmático e Designing Data-Intensive Applications nas partes em que tinha dúvida sobre melhores práticas.

Nas respostas teóricas deste README o fluxo foi o inverso do código: as respostas partem do meu raciocínio e das decisões que tomei durante a prova, e pedi pra IA enriquecê-las com os exemplos reais do repositório — apontar em qual arquivo cada decisão está materializada e conferir que nada afirmado aqui divergia do que foi implementado — e melhorar a clareza do que escrevi, mantendo o meu jeito de escrever.


## Extras

- Rate limit: `POST /alertas/estoque-baixo/verificar` aceita 3 chamadas por minuto por usuário (INCR+EXPIRE no Redis, fail-open se o Redis cair). Acima disso responde `429` com `Retry-After`. Ajustável via `RATE_LIMIT_VERIFICAR_MAX` e `RATE_LIMIT_VERIFICAR_JANELA`.
- Ordenação: `GET /produtos` aceita `ordenar_por` (`nome`, `quantidade_em_estoque`, `data_atualizacao`) e `ordem` (`asc`/`desc`), resolvidos com `ORDER BY` no banco. No front, os cabeçalhos da tabela são clicáveis.
- Cada tela do front tem um painel "por baixo dos panos" explicando o fluxo real por trás dela.
- Histórico de movimentações: criação e mudança de quantidade gravam movimentação (tipo, quantidade, saldo resultante, usuário) na mesma transação. `GET /produtos/{id}/movimentacoes`, e o agente responde "histórico de movimentações do teclado".
- LLM local opcional no agente: `docker compose --profile llm up` sobe um Ollama; com `AGENTE_LLM_URL` no `.env` o agente tenta o modelo primeiro e degrada pras regras se ele cair. Sem a variável, tudo funciona só com regras.
- Servidor MCP: `uv run python bin/mcp_server.py` expõe as ferramentas do agente via MCP (stdio), como fachada da API REST — mesmo JWT, nenhum acesso direto a banco.

## O que faltou por tempo

- Kong demonstrável: a Questão 1 descreve o gateway; um Kong DB-less no compose, com rota declarativa na frente da API, deixaria a resposta visível na prática.
- Tracing distribuído: logs com request-id e `/metrics` existem; faltou a terceira perna — OpenTelemetry exportando pra um Jaeger/Tempo no compose (instrumentação automática de FastAPI e asyncpg são poucas linhas).
- Usuários de verdade: o JWT autentica uma credencial única do `.env`. Com mais tempo: tabela de usuários com hash bcrypt, refresh token e roles (leitura vs. escrita de estoque) — o `bcrypt` já está nas dependências por isso.
- Entrega real dos alertas: hoje a verificação de estoque baixo grava numa lista no Redis e aparece no console; num ERP real o worker dispararia email/webhook, com idempotência pra não notificar duas vezes o mesmo estado.
- Seed como profile do compose: hoje é um comando manual documentado; um profile `demo` subiria a stack já populada.

## Links do Portfólio

- Portfólio: https://apvillela.github.io/
- GitHub: https://github.com/apvillela
- Projeto destacado — Sentinel: https://github.com/apvillela/aws-ai-agent
- Decifra (orientador de IA que traduz editais da educação pública): https://github.com/apvillela/decifra

O mais representativo é o **Sentinel**, um pipeline serverless de enriquecimento de leads de vendas: leads chegam crus (empresa, setor, tamanho, orçamento) e o Sentinel classifica e pontua cada um cruzando o perfil com uma base de perfis ideais de cliente via RAG, devolvendo score de 0 a 100 com tier (VIP/HOT/COLD) pronto pra dashboard.

As decisões têm paralelo com esta prova. A ingestão (Lambda em TypeScript) é desacoplada do processamento de IA (Lambda em Python com LangChain) por uma fila SQS, pelo mesmo motivo que usei fila aqui: chamada de LLM é lenta e falha, então quem recebe responde rápido e quem enriquece consome no próprio ritmo. O score é determinístico, com pesos explícitos por similaridade, tamanho, setor e orçamento — o agente usa RAG e uma calculator tool, mas a conta é auditável. O resto: DynamoDB, Stream carregando o BigQuery, Looker Studio por cima, infra com AWS SAM e segredos no SSM.

O que eu faria diferente hoje: ficou multi-cloud sem necessidade (AWS pra computação, Gemini/GCP pra LLM e analytics, Pinecone pro vetor) e eu consolidaria, como fiz depois no Decifra com pgvector. Também colocaria observabilidade do agente desde o primeiro dia (prompt, resposta, tokens e latência por lead) e testes de contrato entre as duas Lambdas, porque o schema da mensagem na fila é o tipo de contrato implícito que quebra em silêncio.
