import { parseLotePage, parseOpcoes, type Filtros, type LotePage, type Opcoes } from "./types";

export class ApiError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function decode(response: Response): Promise<Record<string, unknown>> {
  const text = await response.text();
  if (response.ok) {
    if (!text) return {};
    return JSON.parse(text) as Record<string, unknown>;
  }
  let detail = text;
  try {
    const json = JSON.parse(text) as { detail?: unknown };
    if (json.detail != null) detail = String(json.detail);
  } catch {
    /* keep raw */
  }
  throw new ApiError(detail || `HTTP ${response.status}`);
}

function appendList(params: URLSearchParams, key: string, values: string[]) {
  for (const value of values) params.append(key, value);
}

export function imageUrl(loteId: number): string {
  return `/imagens/${loteId}`;
}

export async function fetchOpcoes(): Promise<Opcoes> {
  const response = await fetch("/api/opcoes");
  return parseOpcoes(await decode(response));
}

export async function fetchLotes(
  filtros: Filtros,
  page: number,
  pageSize = 24,
): Promise<LotePage> {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
    somente_interesse: String(filtros.somenteInteresse),
    mostrar_inativos: String(filtros.mostrarInativos),
  });
  const modelo = filtros.modeloContem.trim();
  if (modelo) params.set("modelo_contem", modelo);
  if (filtros.valorMin != null) params.set("valor_min", String(filtros.valorMin));
  if (filtros.valorMax != null) params.set("valor_max", String(filtros.valorMax));
  if (filtros.anoMin != null) params.set("ano_min", String(filtros.anoMin));
  if (filtros.anoMax != null) params.set("ano_max", String(filtros.anoMax));
  appendList(params, "marcas", filtros.marcas);
  appendList(params, "municipios", filtros.municipios);
  appendList(params, "condicoes", filtros.condicoes);
  appendList(params, "status_edital", filtros.statusEdital);
  const response = await fetch(`/api/lotes?${params}`);
  return parseLotePage(await decode(response));
}

export async function setInteresse(loteId: number, flagged: boolean): Promise<void> {
  const response = await fetch(`/api/lotes/${loteId}/interesse`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ flagged }),
  });
  await decode(response);
}
