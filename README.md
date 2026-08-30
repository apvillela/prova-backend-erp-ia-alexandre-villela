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

As migrações rodam sozinhas no `docker compose up` (o container `migrate` executa `alembic upgrade head` antes da API subir). Pra popular o banco com dados de exemplo, rode o seed depois que a stack estiver de pé:

```bash
docker compose run --rm app-1 python bin/seed.py
```

O seed é idempotente: insere 10 produtos de exemplo (com casos úteis pra demo, como estoque zerado e estoque baixo) e não faz nada se o banco já tiver produto.

## Stack e decisões

- **Python 3.11** — versão estável e amplamente suportada pelas libs do ecossistema.
- **FastAPI** — padrão pra API assíncrona: validação integrada com Pydantic, OpenAPI/Swagger de graça e injeção de dependências que simplifica auth e sessão de banco.
- **Pydantic v2 + pydantic-settings** — contrato de entrada/saída da API e settings tipadas lidas do `.env`; v2 é o padrão atual.
- **SQLAlchemy 2 async + asyncpg** — escolhi ORM (em vez de driver puro) porque o CRUD ganha muito de modelo declarativo, e a query complexa continua possível; a variante async + asyncpg existe pra não bloquear o event loop do FastAPI — um driver síncrono travaria todas as requisições durante cada query.
- **Alembic** — schema versionado e migração reproduzível; `create_all()` não altera tabela existente.
- **Redis** — cache de leitura, fila do worker e rate limit, um serviço só pra três papéis.
- **arq** — fila async-native que usa o Redis que já existe; Celery seria peso demais pra um worker.
- **uv + `uv.lock`** — lock reproduzível e build rápido no Docker.
- **Docker / Docker Compose** — a stack inteira sobe com um comando, igual em qualquer máquina.

## Respostas das questões teóricas

### Questão 1 — Arquitetura do módulo de Pedidos e Estoque

Eu dividiria os serviços por capacidade de negócio, não por tabela. A tentação de criar um serviço de Produto, um de Estoque e um de Pedido é grande, mas isso só distribui o acoplamento: pedido e estoque mudam juntos (criar um pedido reserva/baixa estoque, cancelar devolve), então separá-los transformaria uma transação local em uma saga distribuída sem necessidade. Meu critério de corte é: coisas que precisam mudar juntas e ser consistentes juntas ficam no mesmo serviço. Então o novo módulo seria um serviço de **Pedidos e Estoque** (dono das tabelas de produto, estoque e pedido), conversando com os serviços de **Financeiro** e **Clientes** que já existem — cada um dono do seu banco, sem nenhum serviço lendo tabela dos outros. É exatamente o recorte deste repositório: a API é o módulo de Produtos/Estoque e trata financeiro e clientes como serviços externos.

Na comunicação eu usaria as duas formas, com um critério simples: REST síncrono quando a resposta é necessária pra concluir a requisição atual, fila quando o chamador não precisa esperar. Consultar o limite de crédito do cliente antes de aprovar um pedido é síncrono — não dá pra aprovar sem a resposta. Já "pedido aprovado, financeiro precisa faturar" é um evento: publico na fila e o financeiro consome no ritmo dele, sem o módulo de pedidos ficar refém da disponibilidade do outro. O ponto importante do síncrono é não deixar a latência dos outros virar a minha: no endpoint `/resumo` deste repo as três fontes (estoque, financeiro, cliente) são consultadas em paralelo com `asyncio.gather`, cada uma com timeout e retry próprios (com backoff exponencial + jitter, e sem retry pra 4xx que não seja transitório — repetir uma recusa só repete a recusa), e a falha de uma fonte degrada só o próprio campo em vez de derrubar a resposta inteira.

PostgreSQL é a fonte de verdade de cada serviço — um banco por serviço, schema versionado com migração (aqui uso Alembic, rodando num container próprio antes da API subir, porque com N réplicas migrar no startup faria todas correrem pro mesmo lock). Redis entra em quatro papéis, todos presentes neste repo: cache de leitura (as listagens de produtos são cacheadas com invalidação por versão de namespace — escrever bumpa a versão e as chaves velhas expiram por TTL, em vez de varrer com SCAN/DEL), fila de background (o worker `arq` consome as verificações de estoque baixo), rate limit (INCR+EXPIRE por usuário no endpoint de verificação) e, se precisar, pub/sub pra eventos leves e locks distribuídos pra jobs que não podem rodar em duas réplicas ao mesmo tempo. Uma regra que sigo: tudo que está no Redis pode sumir — cache e rate limit aqui são fail-open, se o Redis cair a API continua respondendo direto do Postgres.

O API Gateway (Kong, por exemplo) é o único ponto de entrada externo: ele centraliza TLS, autenticação, rate limit global, roteamento e versionamento de rota, e os serviços ficam numa rede interna sem exposição direta. Isso evita que cada serviço reimplemente essas preocupações e dá um lugar único pra cortar um cliente abusivo ou fazer canary de uma versão nova. Comunicação interna entre serviços não precisa passar pelo gateway — ele existe pra borda.

Observabilidade eu penso em três pernas. Logs estruturados com request-id propagado entre serviços — aqui a API já gera request-id por middleware e loga com ele, que é o que permite seguir uma requisição que atravessou três serviços. Métricas com Prometheus + Grafana — a API já expõe `/metrics` (sem agrupar status code, porque num ERP a diferença entre um 409 e um 422, ou entre 500 e 503, muda a decisão de quem está de plantão). E tracing distribuído com OpenTelemetry (Tempo ou Jaeger) quando a pergunta vira "em qual serviço essa requisição gastou os 2 segundos". Como prioridade de monitoração num ERP: taxa de erro e latência p95/p99 dos fluxos que envolvem dinheiro (criação de pedido, faturamento), profundidade e idade da fila (fila crescendo é incidente silencioso), e divergência de estoque — alertar por sintoma que o usuário sente, não por CPU.

### Questão 2 — Estrutura de pastas de um serviço FastAPI

Uso a estrutura deste repositório, que é o padrão que sigo pra serviço FastAPI de médio porte: um núcleo transversal (`config.py` com settings do `.env`, `database/` com engine e sessão, `caching/` com o cliente Redis, `middlewares/`, `exceptions/`, `logging_config/`) e um diretório `services/` onde cada domínio é uma pasta fechada com `router.py`, `controller.py`, `schemas.py` e `models.py` — aqui: `produtos`, `alertas`, `resumo`, `agente`, `auth`, `health`.

A divisão de responsabilidade é: o router cuida só de HTTP (path, status code, dependências de auth, paginação de query string) e delega; o controller tem a regra de negócio e não conhece HTTP — erro de domínio sobe como exceção própria e um handler central traduz em status code, então o mesmo controller serve pra um endpoint, um worker ou um teste sem carregar `Request` junto; os schemas Pydantic são o contrato de entrada e saída (validação de preço negativo, nome vazio etc. mora neles, não em `if` espalhado); e os models SQLAlchemy ficam isolados na camada de banco. Não criei uma camada `repositories/` separada porque neste porte ela viraria um passa-prato — o controller fala com a sessão direto; se as queries começarem a se repetir entre controllers, aí a camada nasce com motivo.

O ganho de testabilidade aparece direto na suíte: os testes unitários exercitam schemas e controllers sem subir HTTP, e os de integração batem nos endpoints. E manutenção: domínio novo é uma pasta nova em `services/`, sem tocar nas outras — o diff de uma feature fica contido no domínio dela. De princípio, eu diria que é uma separação de camadas inspirada em Clean Architecture e num DDD leve (domínio no centro, HTTP e banco nas bordas), mas sem dogma: apliquei o que paga o próprio custo neste tamanho de serviço, e o resto (repositories, use cases formais) entra quando o serviço crescer pra justificar.

### Questão 3 — asyncio vs threading vs multiprocessing

Os três resolvem concorrência, mas em eixos diferentes. `asyncio` é concorrência cooperativa numa thread só: um event loop alterna entre tarefas nos pontos de `await`, então ele brilha quando o gargalo é esperar I/O — muitas conexões, pouco CPU. É a base deste projeto inteiro (FastAPI + SQLAlchemy async + asyncpg, justamente pra não bloquear o loop), e o exemplo de ERP é o `/resumo`: consultar estoque, financeiro e cliente ao mesmo tempo com `asyncio.gather`, pagando o tempo da fonte mais lenta em vez da soma das três.

`threading` também é pra I/O, mas preemptivo e com threads de verdade do sistema operacional. Por causa do GIL, só uma thread executa bytecode Python por vez, então ele não acelera conta pesada — serve quando preciso de concorrência com código bloqueante que não tem versão async: uma lib síncrona de SFTP, um driver de banco legado, o SDK de um parceiro. No ERP: baixar em paralelo os arquivos de retorno bancário (CNAB) de três bancos usando uma lib que só existe síncrona — jogo cada download numa thread (ou num `run_in_executor`, que é como o mundo async convive com isso) e o processo não fica parado esperando um de cada vez.

`multiprocessing` é pra quando o gargalo é CPU: processos separados, cada um com seu interpretador e seu GIL, usando os núcleos de verdade. O custo é maior (memória não compartilhada, dados atravessam por serialização), então só vale quando a conta é pesada mesmo. No ERP: gerar o relatório mensal consolidado em PDF, ou reprocessar um CSV de milhões de linhas de movimentação de estoque — quebro o arquivo em pedaços e distribuo entre processos. Na prática, num serviço web eu nem uso `multiprocessing` direto dentro da API: mando a tarefa pesada pra fila (aqui o worker `arq`) e quem escala são os workers — a API continua leve respondendo requisições, que é o trabalho dela.

### Questão 9 — Design plugável pra um LLM real

A Parte 5 deste repo já foi implementada com essa pergunta em mente, então a resposta é em boa parte descrever o que está em `services/agente/`. O tool calling é um registry de ferramentas (`ferramentas.py`) onde cada ferramenta declara nome, descrição e schema de parâmetros no mesmo formato de function calling dos provedores — `consultar_estoque_baixo(limite)`, `buscar_produtos(nome, preco_min, preco_max)`, `contar_produtos()`. O executor de cada ferramenta é uma função async que recebe sessão e parâmetros validados. O interpretador atual (`interprete.py`) é determinístico, por regras, e devolve uma `ChamadaFerramenta` com nome, parâmetros e confiança — que é exatamente o contrato que um LLM com function calling devolveria. Plugar um LLM real é trocar essa única camada: em vez das regex, mando a pergunta + o spec das ferramentas pro modelo e recebo a mesma `ChamadaFerramenta`. Router, executor, validação e resposta JSON não mudam.

Sobre MCP: sim, usaria, porque ele resolve o problema de expor as mesmas ferramentas pra N agentes sem escrever N integrações. Na arquitetura da Parte 1, o servidor MCP entra como uma fachada fina ao lado do API Gateway: ele não tem regra de negócio nem acesso a banco — cada tool do MCP chama a API REST do serviço dono do dado (produtos/estoque, financeiro, clientes), passando pelo mesmo gateway, com as mesmas credenciais e permissões de um cliente qualquer. Isso é importante: o agente não ganha um atalho pro banco; ele é só mais um consumidor da API, então toda a autorização, rate limit e auditoria que já existem valem pra ele. O registry de ferramentas deste repo viraria a lista de tools do servidor MCP quase um pra um.

Guardrails: primeiro, o agente deste repo só tem ferramentas de leitura — e manteria essa assimetria num sistema real: consultar é livre, mas qualquer tool mutante (criar pedido, deletar, ajustar estoque) exige confirmação explícita do usuário antes de executar (human in the loop), idealmente com a ação descrita em linguagem natural pra pessoa aprovar o que de fato vai acontecer. Segundo, parâmetros sempre validados por schema (Pydantic) antes de tocar o banco — o modelo alucinar um parâmetro vira 422, não uma query errada. Terceiro, allowlist: o agente só executa ferramentas do registry, nunca SQL ou código arbitrário, e as queries têm limites embutidos (`LIMIT 50` na busca). E pra alucinação de interpretação, o campo `confianca` existe pra isso: abaixo de um piso, ou quando o interpretador não reconhece a pergunta, a resposta é "não entendi, reformule" com as capacidades listadas — errar dizendo que não sabe é barato, errar executando a ferramenta errada não.

Custo, latência e observabilidade com LLM: logar prompt, resposta, ferramenta escolhida, tokens e latência de cada chamada, amarrados ao request-id que já atravessa a aplicação — sem isso não dá nem pra debugar alucinação nem pra saber onde o dinheiro vai. Cache de respostas no Redis pra perguntas repetidas (a mesma invalidação por versão que uso nas listagens serve: mudou o dado, a resposta cacheada morre). E o provedor de IA é uma fonte externa como outra qualquer, então recebe o mesmo tratamento do `/resumo`: timeout, retry com backoff pra erro transitório e fallback quando está fora — que aqui é degradar pro interpretador determinístico por regras, que continua respondendo as perguntas mais comuns. Modelo caro só onde precisa: roteamento/classificação com modelo pequeno, geração com modelo maior.

### Questão 10 — Frente em Go

Reagiria bem, e sem drama: a decisão de linguagem é do problema, não do meu conforto. Pro cenário descrito — ingestão de grande volume de eventos com baixa latência e alto throughput — acho Go uma escolha razoável mesmo. É o tipo de carga onde o modelo de goroutines e channels foi feito pra brilhar: concorrência barata sem a cerimônia de event loop, GC pensado pra pausas curtas, e o binário único estático simplifica deploy e reduz a superfície da imagem (um container FROM scratch de poucos MB contra uma imagem Python com interpretador e dependências). Python com asyncio me atende muito bem em API de negócio — este repo é a prova — mas num pipeline de eventos onde cada microssegundo de overhead por mensagem multiplica por milhões, o GIL e o custo do interpretador viram teto, e eu preferiria não passar o projeto lutando contra a plataforma.

Se eu discordasse — por exemplo, se a análise mostrasse que o gargalo real é I/O de rede e o volume não justifica — eu argumentaria com número, não com preferência: um protótipo pequeno nas duas linguagens, medindo throughput e p99 com carga realista, e o custo de manutenção de introduzir uma segunda linguagem no stack (CI, libs internas, on-call de quem não conhece Go). Se o número desse empate, defenderia ficar em Python pela homogeneidade. Mas alta concorrência com baixo overhead é exatamente o caso onde eu esperaria o Go ganhar, então a discussão provavelmente seria curta.

Como não tenho experiência prévia em Go, me organizaria pra aprender com entrega, não antes dela: primeiro o Tour of Go e o Effective Go pra pegar o idioma (e não escrever "Python com sintaxe de Go"), depois um componente pequeno e de baixo risco em produção — um consumer de fila com contrato bem definido, coberto de teste — antes do serviço crítico. Pediria code review de quem já escreve Go desde o primeiro PR, porque review é onde idioma se aprende de verdade, e usaria as ferramentas que a comunidade já padronizou (gofmt, golangci-lint, a lib padrão antes de framework). E aproveitaria que a frente é nova pra fazer benchmark desde o início — se a promessa da mudança é performance, ela precisa aparecer no gráfico.

## Uso de IA

<!-- TODO(alexandre): descrever o que foi gerado/apoiado por IA e o que foi escrito/revisado manualmente -->


## Extras

- Rate limit: `POST /alertas/estoque-baixo/verificar` aceita 3 chamadas por minuto por usuário (INCR+EXPIRE no Redis, fail-open se o Redis cair). Acima disso responde `429` com `Retry-After`. Ajustável via `RATE_LIMIT_VERIFICAR_MAX` e `RATE_LIMIT_VERIFICAR_JANELA`.
- Ordenação: `GET /produtos` aceita `ordenar_por` (`nome`, `quantidade_em_estoque`, `data_atualizacao`) e `ordem` (`asc`/`desc`), resolvidos com `ORDER BY` no banco. No front, os cabeçalhos da tabela são clicáveis.
- Cada tela do front tem um painel "por baixo dos panos" explicando o fluxo real por trás dela.

## Links do Portfólio

- Portfólio: https://apvillela.github.io/
- GitHub: https://github.com/apvillela
- Projeto destacado — Sentinel: https://github.com/apvillela/aws-ai-agent
- Decifra (orientador de IA que traduz editais da educação pública): https://github.com/apvillela/decifra

O projeto que considero mais representativo é o **Sentinel**, um pipeline serverless de enriquecimento de leads de vendas. O problema que ele resolve: leads chegam crus (empresa, setor, tamanho, orçamento) e alguém precisa decidir quem atacar primeiro — o Sentinel classifica e pontua cada lead automaticamente, cruzando o perfil com uma base de perfis ideais de cliente via RAG e devolvendo um score de 0 a 100 com tier (VIP/HOT/COLD) pronto pra dashboard.

As principais decisões técnicas têm bastante paralelo com esta prova. A ingestão (Lambda em TypeScript no API Gateway) é desacoplada do processamento de IA (Lambda em Python com LangChain) por uma fila SQS — pelo mesmo motivo que usei fila aqui: a chamada de LLM é lenta e falha, então quem recebe o lead responde rápido e quem enriquece consome no próprio ritmo, com retry de graça pela fila. O score em si é determinístico (pesos explícitos por similaridade, tamanho, setor e orçamento), não uma nota que o modelo inventa — o agente ReAct usa o RAG e uma calculator tool, mas a conta é auditável, porque score de venda que ninguém consegue explicar não sustenta decisão de negócio. O resto do fluxo: DynamoDB pra armazenar, Stream disparando carga no BigQuery e Looker Studio por cima, tudo provisionado com AWS SAM e segredos no SSM.

O que eu faria diferente hoje: o projeto ficou multi-cloud sem necessidade (AWS pra computação, Gemini/GCP pra LLM e analytics, Pinecone pro vetor) — cada fronteira dessas é uma credencial, uma cobrança e um ponto de falha a mais, e hoje eu consolidaria (pgvector no lugar do Pinecone, por exemplo, como fiz depois no Decifra). Também investiria mais cedo em observabilidade do agente — logar prompt, resposta, tokens e latência por lead desde o primeiro dia, que é caro de adicionar depois e barato de fazer no começo — e colocaria testes de contrato entre a Lambda de ingestão e a de IA, porque o schema da mensagem na fila é exatamente o tipo de contrato implícito que quebra em silêncio.
