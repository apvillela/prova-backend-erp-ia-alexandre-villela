const TOKEN_KEY = "erp_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null): void {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  const response = await fetch(`/api${path}`, { ...options, headers });

  if (response.status === 401 && path !== "/auth/login") {
    setToken(null);
    window.dispatchEvent(new Event("erp:logout"));
  }
  if (!response.ok) {
    let message = `Erro ${response.status}`;
    try {
      const body = await response.json();
      if (Array.isArray(body.detail)) message = body.detail.map((d: { msg: string }) => d.msg).join(" ");
    } catch {
      /* corpo não-JSON: mantém a mensagem padrão */
    }
    throw new ApiError(response.status, message);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export interface ComponentStatus {
  healthy: boolean;
  detail: string | null;
}

export interface Readiness {
  ready: boolean;
  postgres: ComponentStatus;
  redis: ComponentStatus;
  worker: ComponentStatus;
}

export interface Produto {
  id: number;
  nome: string;
  preco: string;
  quantidade_em_estoque: number;
  data_criacao: string;
  data_atualizacao: string;
}

export interface ProdutosPage {
  items: Produto[];
  total: number;
  page: number;
  size: number;
}

export interface Alerta {
  verificado_em: string;
  limite: number;
  produtos: { id: number; nome: string; quantidade_em_estoque: number }[];
}

export interface FonteResultado {
  disponivel: boolean;
  tentativas: number;
  dados: Record<string, unknown> | null;
  erro: string | null;
}

export interface Consolidado {
  completo: boolean;
  estoque: FonteResultado;
  financeiro: FonteResultado;
  cliente: FonteResultado;
}

export interface RespostaAgente {
  pergunta: string;
  ferramenta: string | null;
  parametros: Record<string, unknown>;
  confianca: number;
  resultado: unknown;
  mensagem: string;
}
