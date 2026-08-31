import { FormEvent, useCallback, useEffect, useState } from "react";
import { fetchLotes, fetchOpcoes, setInteresse } from "./api";
import { FilterPanel } from "./FilterPanel";
import { LoteCard } from "./LoteCard";
import { LoteDetailDialog } from "./LoteDetailDialog";
import { emptyFiltros, type Filtros, type Lote, type Opcoes } from "./types";
import "./App.css";

function useCompact() {
  const [compact, setCompact] = useState(
    () => window.matchMedia("(max-width: 599px)").matches,
  );
  useEffect(() => {
    const mq = window.matchMedia("(max-width: 599px)");
    const onChange = () => setCompact(mq.matches);
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);
  return compact;
}

function fmtInt(value: number): string {
  return value.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ".");
}

function statusDefault(opcoes: Opcoes | null): string[] {
  const status = opcoes?.statusEdital ?? [];
  return ["Publicado", "Em Andamento"].filter((name) => status.includes(name));
}

export function App() {
  const compact = useCompact();
  const [filtros, setFiltros] = useState<Filtros>(emptyFiltros);
  const [opcoes, setOpcoes] = useState<Opcoes | null>(null);
  const [lotes, setLotes] = useState<Lote[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [interesseCount, setInteresseCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [detail, setDetail] = useState<Lote | null>(null);

  const pageSize = 24;
  const maxPage = total <= 0 ? 1 : Math.ceil(total / pageSize);

  const load = useCallback(async (nextFiltros: Filtros, nextPage: number) => {
    setLoading(true);
    setError(null);
    try {
      let result = await fetchLotes(nextFiltros, nextPage, pageSize);
      let pageUsed = nextPage;
      const max = result.total <= 0 ? 1 : Math.ceil(result.total / pageSize);
      if (nextPage > max) {
        pageUsed = max;
        result = await fetchLotes(nextFiltros, pageUsed, pageSize);
      }
      setLotes(result.lotes);
      setTotal(result.total);
      setPage(pageUsed);
      setInteresseCount(result.interesseCount);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  const bootstrap = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const nextOpcoes = await fetchOpcoes();
      setOpcoes(nextOpcoes);
      setInteresseCount(nextOpcoes.interesseCount);
      const nextFiltros = { ...emptyFiltros(), statusEdital: statusDefault(nextOpcoes) };
      setFiltros(nextFiltros);
      await load(nextFiltros, 1);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setLoading(false);
    }
  }, [load]);

  useEffect(() => {
    void bootstrap();
  }, [bootstrap]);

  function applySearch(value: string) {
    const next = { ...filtros, modeloContem: value.trim() };
    setFiltros(next);
    setSearch(value.trim());
    void load(next, 1);
  }

  function onSearchSubmit(e: FormEvent) {
    e.preventDefault();
    applySearch(search);
  }

  return (
    <div className="shell">
      <header className={compact ? "topbar" : "topbar topbar--wide"}>
        {compact && (
          <button type="button" className="icon-btn" aria-label="Filtros" onClick={() => setDrawerOpen(true)}>
            <span className="material-symbols-outlined">menu</span>
          </button>
        )}
        <h1 className="topbar__title">Lotes DETRAN/MG</h1>
        {!compact && (
          <form className="topbar__search" onSubmit={onSearchSubmit}>
            <span className="material-symbols-outlined">search</span>
            <input
              value={search}
              placeholder="Modelo contém"
              onChange={(e) => setSearch(e.target.value)}
            />
          </form>
        )}
        <div className="topbar__actions">
          {compact && (
            <button
              type="button"
              className="icon-btn"
              aria-label="Buscar modelo"
              onClick={() => setSearchOpen(true)}
            >
              <span className="material-symbols-outlined">search</span>
            </button>
          )}
          <span className="badge">
            <span className="material-symbols-outlined fill" style={{ color: "var(--md-sys-color-tertiary)" }}>
              star
            </span>
            {interesseCount > 0 && <span className="badge__count">{interesseCount}</span>}
          </span>
          <label className="switch">
            {!compact && <span>Somente interesse</span>}
            <input
              type="checkbox"
              checked={filtros.somenteInteresse}
              onChange={(e) => {
                const next = { ...filtros, somenteInteresse: e.target.checked };
                setFiltros(next);
                void load(next, 1);
              }}
            />
          </label>
        </div>
      </header>

      <div className="layout">
        {compact && drawerOpen && (
          <button type="button" className="scrim" aria-label="Fechar filtros" onClick={() => setDrawerOpen(false)} />
        )}
        {(!compact || drawerOpen) && (
          <aside className={compact ? "drawer drawer--modal" : "drawer"}>
            <FilterPanel
              filtros={filtros}
              opcoes={opcoes}
              onChange={setFiltros}
              onApply={(next) => {
                setFiltros(next);
                setDrawerOpen(false);
                void load(next, 1);
              }}
              onClear={() => {
                const next = {
                  ...emptyFiltros(),
                  statusEdital: statusDefault(opcoes),
                };
                setFiltros(next);
                setSearch("");
                setDrawerOpen(false);
                void load(next, 1);
              }}
            />
          </aside>
        )}

        <main className="main">
          <div className={compact ? "main__inner" : "main__inner"}>
            {error && lotes.length === 0 ? (
              <div className="error">
                <span className="material-symbols-outlined">cloud_off</span>
                <h2>Banco indisponível</h2>
                <p>{error}</p>
                <p>
                  Suba o Postgres (`docker compose up -d`), rode `python -m detran_scraper.run
                  --lotes` e `python -m detran_ui`.
                </p>
                <button type="button" className="btn btn--filled" onClick={() => void bootstrap()}>
                  Tentar de novo
                </button>
              </div>
            ) : (
              <>
                <div className="toolbar">
                  <h2>{fmtInt(total)} lotes</h2>
                  <span className="chip">
                    <span className="material-symbols-outlined fill">star</span>
                    {interesseCount} de interesse
                  </span>
                  {loading && <span className="spinner" aria-label="Carregando" />}
                </div>
                {total === 0 && !loading ? (
                  <div className="empty">
                    <span className="material-symbols-outlined">search_off</span>
                    <p>Nenhum lote com esses filtros.</p>
                  </div>
                ) : (
                  <div className={compact ? "list" : "grid"}>
                    {lotes.map((lote) => (
                      <LoteCard
                        key={lote.loteId}
                        lote={lote}
                        onOpen={() => setDetail(lote)}
                        onToggle={() => {
                          void setInteresse(lote.loteId, !lote.interesse).then(() =>
                            load(filtros, page),
                          );
                        }}
                      />
                    ))}
                  </div>
                )}
                {maxPage > 1 && (
                  <div className="pager">
                    <button
                      type="button"
                      className="icon-btn icon-btn--tonal"
                      disabled={page <= 1}
                      onClick={() => void load(filtros, page - 1)}
                    >
                      <span className="material-symbols-outlined">chevron_left</span>
                    </button>
                    <span>
                      {page} / {maxPage}
                    </span>
                    <button
                      type="button"
                      className="icon-btn icon-btn--tonal"
                      disabled={page >= maxPage}
                      onClick={() => void load(filtros, page + 1)}
                    >
                      <span className="material-symbols-outlined">chevron_right</span>
                    </button>
                  </div>
                )}
              </>
            )}
          </div>
        </main>
      </div>

      {searchOpen && (
        <div className="search-sheet">
          <div className="search-sheet__row">
            <button type="button" className="icon-btn" onClick={() => setSearchOpen(false)}>
              <span className="material-symbols-outlined">arrow_back</span>
            </button>
            <input
              autoFocus
              value={search}
              placeholder="Modelo contém"
              onChange={(e) => setSearch(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  applySearch(search);
                  setSearchOpen(false);
                }
              }}
            />
            <button type="button" className="icon-btn" onClick={() => setSearch("")}>
              <span className="material-symbols-outlined">close</span>
            </button>
          </div>
          <button
            type="button"
            className="btn btn--filled"
            onClick={() => {
              applySearch(search);
              setSearchOpen(false);
            }}
          >
            Buscar
          </button>
        </div>
      )}

      {detail && <LoteDetailDialog lote={detail} onClose={() => setDetail(null)} />}
    </div>
  );
}
