export type Filtros = {
  marcas: string[];
  modeloContem: string;
  municipios: string[];
  condicoes: string[];
  statusEdital: string[];
  valorMin: number | null;
  valorMax: number | null;
  anoMin: number | null;
  anoMax: number | null;
  somenteInteresse: boolean;
};

export type Opcoes = {
  marcas: string[];
  municipios: string[];
  condicoes: string[];
  statusEdital: string[];
  interesseCount: number;
};

export type Lote = {
  loteId: number;
  leilaoId: number;
  numeroLote: string;
  condicao: string;
  marcaModelo: string;
  valorFmt: string;
  urlDetalhes: string;
  numeroEdital: string;
  municipio: string;
  patio: string;
  statusEdital: string;
  dataEncerramento: string;
  anoVeiculo: string;
  interesse: boolean;
};

export type LotePage = {
  lotes: Lote[];
  total: number;
  page: number;
  pageSize: number;
  interesseCount: number;
};

export const emptyFiltros = (): Filtros => ({
  marcas: [],
  modeloContem: "",
  municipios: [],
  condicoes: [],
  statusEdital: [],
  valorMin: null,
  valorMax: null,
  anoMin: null,
  anoMax: null,
  somenteInteresse: false,
});

function str(value: unknown, fallback = ""): string {
  if (value == null) return fallback;
  const text = String(value).trim();
  return text === "" ? fallback : text;
}

function fmtDate(value: unknown): string {
  if (value == null) return "—";
  const text = String(value);
  return text.length >= 10 ? text.slice(0, 10) : text;
}

export function parseOpcoes(json: Record<string, unknown>): Opcoes {
  const list = (key: string) =>
    Array.isArray(json[key]) ? json[key].map((v) => String(v)) : [];
  return {
    marcas: list("marcas"),
    municipios: list("municipios"),
    condicoes: list("condicoes"),
    statusEdital: list("status_edital"),
    interesseCount: Number(json.interesse_count ?? 0),
  };
}

export function parseLote(json: Record<string, unknown>): Lote {
  return {
    loteId: Number(json.lote_id),
    leilaoId: Number(json.leilao_id ?? 0),
    numeroLote: str(json.numero_lote),
    condicao: str(json.condicao, "—"),
    marcaModelo: str(json.marca_modelo),
    valorFmt: str(json.valor_fmt, "—"),
    urlDetalhes: str(json.url_detalhes),
    numeroEdital: str(json.numero_edital),
    municipio: str(json.municipio),
    patio: str(json.patio),
    statusEdital: str(json.status_edital, "—"),
    dataEncerramento: fmtDate(json.data_encerramento),
    anoVeiculo: str(json.ano_veiculo, "—"),
    interesse: json.interesse === true,
  };
}

export function parseLotePage(json: Record<string, unknown>): LotePage {
  const raw = Array.isArray(json.lotes) ? json.lotes : [];
  return {
    lotes: raw.map((item) => parseLote(item as Record<string, unknown>)),
    total: Number(json.total ?? 0),
    page: Number(json.page ?? 1),
    pageSize: Number(json.page_size ?? 24),
    interesseCount: Number(json.interesse_count ?? 0),
  };
}
