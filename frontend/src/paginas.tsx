import { useCallback, useEffect, useState } from "react";
import {
  Alerta,
  api,
  Resumo as ResumoDto,
  FonteResultado,
  Produto,
  ProdutosPage,
  Readiness,
  RespostaAgente,
} from "./api";

function useErro(): [string, (e: unknown) => void, () => void] {
  const [erro, setErro] = useState("");
  return [
    erro,
    (e: unknown) => setErro(e instanceof Error ? e.message : "Erro inesperado"),
    () => setErro(""),
  ];
}

/* ---------------- Painel ---------------- */

export function Painel({ readiness }: { readiness: Readiness | null }) {
  const [totalProdutos, setTotalProdutos] = useState<number | null>(null);
  const [alertas, setAlertas] = useState<Alerta[]>([]);
  const [verificando, setVerificando] = useState(false);
  const [erro, capturar, limpar] = useErro();

  const carregar = useCallback(async () => {
    try {
      const [pagina, listaAlertas] = await Promise.all([
        api<ProdutosPage>("/produtos?size=1"),
        api<Alerta[]>("/alertas/estoque-baixo?quantidade=5"),
      ]);
      setTotalProdutos(pagina.total);
      setAlertas(listaAlertas);
      limpar();
    } catch (e) {
      capturar(e);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    carregar();
  }, [carregar]);

  async function verificarAgora() {
    setVerificando(true);
    try {
      await api("/alertas/estoque-baixo/verificar", { method: "POST" });
      setTimeout(carregar, 1500);
    } catch (e) {
      capturar(e);
    } finally {
      setVerificando(false);
    }
  }

  const ultimo = alertas[0];

  return (
    <>
      <h1>Painel</h1>
      <p className="subtitulo">
        Estado dos serviços e do estoque. O worker verifica o estoque a cada 5 minutos; a
        verificação também pode ser enfileirada agora.
      </p>
      {erro && <p className="mensagem erro-msg">{erro}</p>}
      <div className="grade">
        <div className="cartao">
          <div className="rotulo">produtos cadastrados</div>
          <div className="valor">{totalProdutos ?? "–"}</div>
        </div>
        <div className="cartao">
          <div className="rotulo">itens em alerta de estoque</div>
          <div className={`valor ${ultimo && ultimo.produtos.length > 0 ? "ambar" : "ok"}`}>
            {ultimo ? ultimo.produtos.length : "–"}
          </div>
          <div className="detalhe">
            {ultimo
              ? `verificado em ${new Date(ultimo.verificado_em).toLocaleTimeString("pt-BR")}`
              : "nenhuma verificação registrada"}
          </div>
        </div>
        <div className="cartao">
          <div className="rotulo">fila de tarefas</div>
          <div className={`valor ${readiness?.worker.healthy ? "ok" : "erro"}`}>
            {readiness?.worker.healthy ? "ativa" : "parada"}
          </div>
          <div className="detalhe">{readiness?.worker.detail ?? "heartbeat do worker via redis"}</div>
        </div>
      </div>
      <div className="linha-form">
        <button className="botao" onClick={verificarAgora} disabled={verificando}>
          {verificando ? "Enfileirando…" : "Verificar estoque agora"}
        </button>
        <button className="botao vazado" onClick={carregar}>
          Atualizar
        </button>
      </div>
      {alertas.length > 0 && (
        <table className="tabela">
          <thead>
            <tr>
              <th>verificação</th>
              <th className="num">limite</th>
              <th>produtos abaixo do limite</th>
            </tr>
          </thead>
          <tbody>
            {alertas.map((a) => (
              <tr key={a.verificado_em}>
                <td>{new Date(a.verificado_em).toLocaleString("pt-BR")}</td>
                <td className="num">{a.limite}</td>
                <td>
                  {a.produtos.length === 0
                    ? "nenhum"
                    : a.produtos.map((p) => `${p.nome} (${p.quantidade_em_estoque})`).join(", ")}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}

/* ---------------- Produtos ---------------- */

const FORM_VAZIO = { nome: "", preco: "", quantidade_em_estoque: "" };

export function Produtos() {
  const [pagina, setPagina] = useState<ProdutosPage | null>(null);
  const [filtroNome, setFiltroNome] = useState("");
  const [soEstoqueBaixo, setSoEstoqueBaixo] = useState(false);
  const [numeroPagina, setNumeroPagina] = useState(1);
  const [form, setForm] = useState(FORM_VAZIO);
  const [editando, setEditando] = useState<number | null>(null);
  const [erro, capturar, limpar] = useErro();

  const carregar = useCallback(async () => {
    const params = new URLSearchParams({ page: String(numeroPagina), size: "10" });
    if (filtroNome) params.set("nome", filtroNome);
    if (soEstoqueBaixo) params.set("estoque_abaixo_de", "10");
    try {
      setPagina(await api<ProdutosPage>(`/produtos?${params}`));
      limpar();
    } catch (e) {
      capturar(e);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [numeroPagina, filtroNome, soEstoqueBaixo]);

  useEffect(() => {
    carregar();
  }, [carregar]);

  async function salvar(e: React.FormEvent) {
    e.preventDefault();
    const corpo = {
      nome: form.nome,
      preco: form.preco.replace(",", "."),
      quantidade_em_estoque: Number(form.quantidade_em_estoque || 0),
    };
    try {
      if (editando === null) {
        await api("/produtos", { method: "POST", body: JSON.stringify(corpo) });
      } else {
        await api(`/produtos/${editando}`, { method: "PATCH", body: JSON.stringify(corpo) });
      }
      setForm(FORM_VAZIO);
      setEditando(null);
      carregar();
    } catch (err) {
      capturar(err);
    }
  }

  async function excluir(id: number) {
    if (!confirm("Excluir este produto?")) return;
    try {
      await api(`/produtos/${id}`, { method: "DELETE" });
      carregar();
    } catch (err) {
      capturar(err);
    }
  }

  function editar(p: Produto) {
    setEditando(p.id);
    setForm({
      nome: p.nome,
      preco: p.preco,
      quantidade_em_estoque: String(p.quantidade_em_estoque),
    });
  }

  const totalPaginas = pagina ? Math.max(1, Math.ceil(pagina.total / pagina.size)) : 1;

  return (
    <>
      <h1>Produtos</h1>
      <p className="subtitulo">
        CRUD sobre PostgreSQL com leitura cacheada no Redis. A barra indica o nível de estoque;
        abaixo de 10 unidades o item entra no alerta do worker.
      </p>
      <form className="linha-form" onSubmit={salvar}>
        <input
          placeholder="nome"
          value={form.nome}
          onChange={(e) => setForm({ ...form, nome: e.target.value })}
          required
        />
        <input
          placeholder="preço (ex: 199.90)"
          value={form.preco}
          onChange={(e) => setForm({ ...form, preco: e.target.value })}
          required
          style={{ width: 140 }}
        />
        <input
          placeholder="estoque"
          type="number"
          min={0}
          value={form.quantidade_em_estoque}
          onChange={(e) => setForm({ ...form, quantidade_em_estoque: e.target.value })}
          style={{ width: 100 }}
        />
        <button className="botao">{editando === null ? "Adicionar" : "Salvar edição"}</button>
        {editando !== null && (
          <button
            type="button"
            className="botao vazado"
            onClick={() => {
              setEditando(null);
              setForm(FORM_VAZIO);
            }}
          >
            Cancelar
          </button>
        )}
      </form>
      <div className="linha-form">
        <input
          placeholder="filtrar por nome"
          value={filtroNome}
          onChange={(e) => {
            setNumeroPagina(1);
            setFiltroNome(e.target.value);
          }}
        />
        <label className="mensagem" style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <input
            type="checkbox"
            checked={soEstoqueBaixo}
            onChange={(e) => {
              setNumeroPagina(1);
              setSoEstoqueBaixo(e.target.checked);
            }}
          />
          só estoque baixo (&lt;10)
        </label>
      </div>
      {erro && <p className="mensagem erro-msg">{erro}</p>}
      <table className="tabela">
        <thead>
          <tr>
            <th>nome</th>
            <th className="num">preço</th>
            <th>estoque</th>
            <th className="num">atualizado</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {pagina?.items.map((p) => (
            <tr key={p.id}>
              <td>{p.nome}</td>
              <td className="num">R$ {p.preco}</td>
              <td>
                <span
                  className={`barra-estoque ${
                    p.quantidade_em_estoque === 0
                      ? "zerado"
                      : p.quantidade_em_estoque < 10
                        ? "baixo"
                        : ""
                  }`}
                  style={{ width: Math.max(4, Math.min(p.quantidade_em_estoque, 60)) }}
                />
                {p.quantidade_em_estoque}
              </td>
              <td className="num">{new Date(p.data_atualizacao).toLocaleDateString("pt-BR")}</td>
              <td>
                <div className="acoes-linha">
                  <button onClick={() => editar(p)}>editar</button>
                  <button onClick={() => excluir(p.id)}>excluir</button>
                </div>
              </td>
            </tr>
          ))}
          {pagina && pagina.items.length === 0 && (
            <tr>
              <td colSpan={5} className="mensagem">
                Nenhum produto encontrado. Adicione o primeiro no formulário acima.
              </td>
            </tr>
          )}
        </tbody>
      </table>
      <div className="paginacao">
        <button
          className="chip"
          disabled={numeroPagina <= 1}
          onClick={() => setNumeroPagina((n) => n - 1)}
        >
          ← anterior
        </button>
        <span>
          página {numeroPagina} de {totalPaginas} · {pagina?.total ?? 0} produto(s)
        </span>
        <button
          className="chip"
          disabled={numeroPagina >= totalPaginas}
          onClick={() => setNumeroPagina((n) => n + 1)}
        >
          próxima →
        </button>
      </div>
    </>
  );
}

/* ---------------- Agente ---------------- */

const EXEMPLOS = [
  "quais produtos estão com estoque abaixo de 10 unidades?",
  "quantos produtos temos cadastrados?",
  "produtos entre 50 e 500",
  "quais são mais baratos que 100?",
];

export function Agente() {
  const [pergunta, setPergunta] = useState("");
  const [resposta, setResposta] = useState<RespostaAgente | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, capturar, limpar] = useErro();

  async function perguntar(texto: string) {
    setCarregando(true);
    setPergunta(texto);
    try {
      setResposta(
        await api<RespostaAgente>("/agente/perguntar", {
          method: "POST",
          body: JSON.stringify({ pergunta: texto }),
        }),
      );
      limpar();
    } catch (e) {
      capturar(e);
    } finally {
      setCarregando(false);
    }
  }

  return (
    <>
      <h1>Agente</h1>
      <p className="subtitulo">
        Pergunta em linguagem natural → interpretação determinística → ferramenta estruturada →
        consulta no banco. Sem LLM externo; a camada de interpretação é o único ponto a trocar por
        um modelo real.
      </p>
      <form
        className="linha-form"
        onSubmit={(e) => {
          e.preventDefault();
          if (pergunta.trim()) perguntar(pergunta.trim());
        }}
      >
        <input
          style={{ flex: 1, minWidth: 240 }}
          placeholder="pergunte sobre os produtos…"
          value={pergunta}
          onChange={(e) => setPergunta(e.target.value)}
        />
        <button className="botao" disabled={carregando || !pergunta.trim()}>
          {carregando ? "Consultando…" : "Perguntar"}
        </button>
      </form>
      <div className="chips">
        {EXEMPLOS.map((ex) => (
          <button key={ex} className="chip" onClick={() => perguntar(ex)}>
            {ex}
          </button>
        ))}
      </div>
      {erro && <p className="mensagem erro-msg">{erro}</p>}
      {resposta && (
        <>
          <div className="traducao">
            {resposta.ferramenta ? (
              <>
                → {resposta.ferramenta}({JSON.stringify(resposta.parametros)}){" "}
                <span className="conf">confiança {resposta.confianca.toFixed(2)}</span>
              </>
            ) : (
              resposta.mensagem
            )}
          </div>
          {resposta.resultado != null && (
            <pre className="resultado">{JSON.stringify(resposta.resultado, null, 2)}</pre>
          )}
        </>
      )}
    </>
  );
}

/* ---------------- Resumo ---------------- */

function CartaoFonte({ nome, fonte }: { nome: string; fonte: FonteResultado }) {
  return (
    <div className={`fonte ${fonte.disponivel ? "" : "indisponivel"}`}>
      <span className="tag-servico">
        <span className={`luz ${fonte.disponivel ? "ok" : "erro"}`} />
        {nome}
      </span>
      <dl>
        <dt>tentativas</dt>
        <dd>{fonte.tentativas}</dd>
        {fonte.erro && (
          <>
            <dt>erro</dt>
            <dd>{fonte.erro}</dd>
          </>
        )}
        {Object.entries(fonte.dados ?? {}).map(([chave, valor]) => (
          <span key={chave} style={{ display: "contents" }}>
            <dt>{chave}</dt>
            <dd>{String(valor)}</dd>
          </span>
        ))}
      </dl>
    </div>
  );
}

export function Resumo() {
  const [clienteId, setClienteId] = useState("1");
  const [produtoId, setProdutoId] = useState("1");
  const [dados, setDados] = useState<ResumoDto | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, capturar, limpar] = useErro();

  async function consultar(e: React.FormEvent) {
    e.preventDefault();
    setCarregando(true);
    try {
      setDados(
        await api<ResumoDto>(`/resumo/${clienteId}?produto_id=${produtoId}`),
      );
      limpar();
    } catch (err) {
      capturar(err);
    } finally {
      setCarregando(false);
    }
  }

  return (
    <>
      <h1>Resumo</h1>
      <p className="subtitulo">
        Consulta as três fontes (estoque, financeiro, cliente) em paralelo com asyncio.gather,
        timeout individual e retry. Se uma fonte falhar, a resposta degrada só naquele campo.
      </p>
      <form className="linha-form" onSubmit={consultar}>
        <input
          type="number"
          min={1}
          value={clienteId}
          onChange={(e) => setClienteId(e.target.value)}
          style={{ width: 130 }}
          aria-label="id do cliente"
        />
        <input
          type="number"
          min={1}
          value={produtoId}
          onChange={(e) => setProdutoId(e.target.value)}
          style={{ width: 130 }}
          aria-label="id do produto"
        />
        <button className="botao" disabled={carregando}>
          {carregando ? "Consultando…" : "Consultar fontes"}
        </button>
      </form>
      {erro && <p className="mensagem erro-msg">{erro}</p>}
      {dados && (
        <>
          <p className="mensagem">
            resposta {dados.completo ? "completa" : "parcial — alguma fonte degradou"}
          </p>
          <div className="fontes">
            <CartaoFonte nome="estoque" fonte={dados.estoque} />
            <CartaoFonte nome="financeiro" fonte={dados.financeiro} />
            <CartaoFonte nome="cliente" fonte={dados.cliente} />
          </div>
        </>
      )}
    </>
  );
}
