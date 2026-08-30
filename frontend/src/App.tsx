import { useCallback, useEffect, useState } from "react";
import { api, getToken, Readiness, setToken } from "./api";
import { Agente, Resumo, Painel, Produtos } from "./paginas";
import header from "../assets/header.png";
import logo from "../assets/ipm_logo.jpeg";

const ABAS = ["painel", "produtos", "agente", "resumo"] as const;
type Aba = (typeof ABAS)[number];

function Login({ aoEntrar }: { aoEntrar: () => void }) {
  const [usuario, setUsuario] = useState("");
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState("");
  const [enviando, setEnviando] = useState(false);

  async function entrar(e: React.FormEvent) {
    e.preventDefault();
    setEnviando(true);
    setErro("");
    try {
      const { access_token } = await api<{ access_token: string }>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ username: usuario, password: senha }),
      });
      setToken(access_token);
      aoEntrar();
    } catch (err) {
      setErro(err instanceof Error ? err.message : "Falha no login");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="tela-login">
      <div className="cartao-login">
        <img className="banner-login" src={header} alt="IPM — Transformando o futuro de cidades e pessoas" />
        <div className="conteudo">
        <h1>Produtos & Estoque</h1>
        <p className="subtitulo" style={{ marginBottom: 0 }}>
          Console de operação do módulo de ERP.
        </p>
        <form onSubmit={entrar}>
          <input
            placeholder="usuário"
            value={usuario}
            onChange={(e) => setUsuario(e.target.value)}
            autoFocus
          />
          <input
            placeholder="senha"
            type="password"
            value={senha}
            onChange={(e) => setSenha(e.target.value)}
          />
          <button className="botao" disabled={enviando || !usuario || !senha}>
            {enviando ? "Entrando…" : "Entrar"}
          </button>
        </form>
        {erro && <p className="erro-form">{erro}</p>}
        <p className="aviso">credenciais padrão do .env: lidertecnica / password123!</p>
        </div>
      </div>
    </div>
  );
}

function TagServico({ nome, saudavel }: { nome: string; saudavel: boolean | null }) {
  const estado = saudavel === null ? "" : saudavel ? "ok" : "erro";
  return (
    <span className="tag-servico">
      <span className={`luz ${estado}`} />
      {nome}
    </span>
  );
}

export default function App() {
  const [autenticado, setAutenticado] = useState(() => getToken() !== null);
  const [aba, setAba] = useState<Aba>("painel");
  const [readiness, setReadiness] = useState<Readiness | null>(null);
  const [apiViva, setApiViva] = useState<boolean | null>(null);

  const consultarSaude = useCallback(async () => {
    try {
      const dados = await api<Readiness>("/health/readiness");
      setReadiness(dados);
      setApiViva(true);
    } catch {
      setReadiness(null);
      setApiViva(false);
    }
  }, []);

  useEffect(() => {
    consultarSaude();
    const intervalo = setInterval(consultarSaude, 5000);
    return () => clearInterval(intervalo);
  }, [consultarSaude]);

  useEffect(() => {
    const sair = () => setAutenticado(false);
    window.addEventListener("erp:logout", sair);
    return () => window.removeEventListener("erp:logout", sair);
  }, []);

  if (!autenticado) return <Login aoEntrar={() => setAutenticado(true)} />;

  return (
    <>
      <header className="trilho">
        <div className="marca">
          <img className="logo-ipm" src={logo} alt="IPM" />
          <span>
            Produtos & Estoque
            <small>módulo erp · console de operação</small>
          </span>
        </div>
        <TagServico nome="api" saudavel={apiViva} />
        <TagServico nome="postgres" saudavel={readiness?.postgres.healthy ?? null} />
        <TagServico nome="redis" saudavel={readiness?.redis.healthy ?? null} />
        <TagServico nome="worker" saudavel={readiness?.worker.healthy ?? null} />
        <button
          className="sair"
          onClick={() => {
            setToken(null);
            setAutenticado(false);
          }}
        >
          sair
        </button>
      </header>
      <nav className="abas">
        {ABAS.map((a) => (
          <button key={a} className={`aba ${a === aba ? "ativa" : ""}`} onClick={() => setAba(a)}>
            {a}
          </button>
        ))}
      </nav>
      <main>
        {aba === "painel" && <Painel readiness={readiness} />}
        {aba === "produtos" && <Produtos />}
        {aba === "agente" && <Agente />}
        {aba === "resumo" && <Resumo />}
      </main>
    </>
  );
}
