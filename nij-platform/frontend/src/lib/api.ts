import axios from "axios";

const BASE = import.meta.env.VITE_API_URL ?? "/api";

export const http = axios.create({ baseURL: BASE });

// Injeta token em toda requisição
http.interceptors.request.use((cfg) => {
  const token = localStorage.getItem("access");
  if (token) cfg.headers.Authorization = `Bearer ${token}`;
  return cfg;
});

// Refresh automático em 401
http.interceptors.response.use(
  (r) => r,
  async (err) => {
    const orig = err.config;
    if (err.response?.status === 401 && !orig._retry) {
      orig._retry = true;
      const refresh = localStorage.getItem("refresh");
      if (refresh) {
        try {
          const { data } = await axios.post(`${BASE}/auth/token/refresh/`, { refresh });
          localStorage.setItem("access", data.access);
          orig.headers.Authorization = `Bearer ${data.access}`;
          return http(orig);
        } catch {
          localStorage.clear();
          window.location.href = "/login";
        }
      }
    }
    return Promise.reject(err);
  }
);

// ── helpers ──────────────────────────────────────────────
export const auth = {
  login: (u: string, p: string) =>
    http.post("/auth/login/", { username: u, password: p }),
  logout: (refresh: string) =>
    http.post("/auth/logout/", { refresh }),
  me: () => http.get("/auth/me/"),
  users: () => http.get("/auth/users/"),
  createUser: (d: object) => http.post("/auth/users/", d),
  deleteUser: (id: number) => http.delete(`/auth/users/${id}/`),
  changePassword: (id: number, d: object) =>
    http.post(`/auth/users/${id}/change-password/`, d),
};

export const docs = {
  upload: (fd: FormData) =>
    http.post("/documents/upload/", fd, {
      headers: { "Content-Type": "multipart/form-data" },
    }),
  get: (id: string) => http.get(`/documents/${id}/`),
  list: () => http.get("/documents/"),
  remove: (id: string) => http.delete(`/documents/${id}/`),
  reprocess: (id: string) => http.post(`/documents/${id}/reprocess/`),
  cancel: (id: string) => http.post(`/documents/${id}/cancel/`),
};

export const audit = {
  logs: (params?: object) => http.get("/audit/logs/", { params }),
};

// ── Banco Central do Brasil (BCB) ──────────────────────────
export interface INPCData {
  data: string;
  valor: number;
  fator: number;
}

export interface INPCSeriesResponse {
  indice: string;
  codigo_bcb: number;
  data_inicio: string;
  data_fim: string;
  registros: number;
  dados: INPCData[];
}

export interface INPCFactorsResponse {
  fatores: Record<string, number>;
  data_atualizacao: string;
  total_datas: number;
}

export const bcb = {
  // Lista séries disponíveis
  listSeries: () => http.get("/analysis/bcb/series/"),
  
  // Busca dados de uma série específica
  getSeriesData: (codigo: number, dataInicio: string, dataFim: string) =>
    http.get("/analysis/bcb/series/data/", {
      params: { codigo, data_inicio: dataInicio, data_fim: dataFim }
    }),
  
  // Busca série do INPC
  getINPC: (dataInicio: string, dataFim: string) =>
    http.get<INPCSeriesResponse>("/analysis/bcb/inpc/", {
      params: { data_inicio: dataInicio, data_fim: dataFim }
    }),
  
  // Calcula fatores de correção INPC para múltiplas datas
  calcularFatoresINPC: (datasPagamento: string[], dataAtualizacao: string) =>
    http.post<INPCFactorsResponse>("/analysis/bcb/inpc/fatores/", {
      datas_pagamento: datasPagamento,
      data_atualizacao: dataAtualizacao
    }),
};
