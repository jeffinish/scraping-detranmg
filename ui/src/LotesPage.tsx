import { FormEvent, useCallback, useEffect, useState } from "react";
import { Link } from "react-router";
import { fetchLotes, fetchOpcoes, setInteresse } from "./api";
import { FilterPanel } from "./FilterPanel";
import { LoteCard } from "./LoteCard";
import { LoteDetailDialog } from "./LoteDetailDialog";
import { Pager } from "./Pager";
import { emptyFiltros, type Filtros, type Lote, type LotePage, type Opcoes } from "./types";
import { useCompact } from "./useCompact";

function fmtInt(value: number): string {
  return value.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ".");
}

function statusDefault(opcoes: Opcoes | null): string[] {
  const status = opcoes?.statusEdital ?? [];
  return ["Publicado", "Em Andamento"].filter((name) => status.includes(name));
}

function scrollToTop() {
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  window.scrollTo({ top: 0, behavior: reduce ? "auto" : "smooth" });
}

function baseFiltros(opcoes: Opcoes | null, interesse: boolean): Filtros {
  return {
    ...emptyFiltros(),
    statusEdital: statusDefault(opcoes),
    somenteInteresse: interesse,
  };
}

export function LotesPage({ interesse = false }: { interesse?: boolean }) {
  const compact = useCompact();
  const [filtros, setFiltros] = useState<Filtros>(() => emptyFiltros());
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

  const load = useCallback(async (nextFiltros: Filtros, nextPage: number): Promise<LotePage | null> => {
    setLoading(true);
    setError(null);
    try {
      const withFlag = { ...nextFiltros, somenteInteresse: interesse };
      let result = await fetchLotes(withFlag, nextPage, pageSize);
      let pageUsed = nextPage;
      const max = result.total <= 0 ? 1 : Math.ceil(result.total / pageSize);
      if (nextPage > max) {
        pageUsed = max;
        result = await fetchLotes(withFlag, pageUsed, pageSize);
      }
      setLotes(result.lotes);
      setTotal(result.total);
      setPage(pageUsed);
      setInteresseCount(result.interesseCount);
      return result;
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      return null;
    } finally {
      setLoading(false);
    }
  }, [interesse]);

  const bootstrap = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const nextOpcoes = await fetchOpcoes();
      setOpcoes(nextOpcoes);
      setInteresseCount(nextOpcoes.interesseCount);
      const nextFiltros = baseFiltros(nextOpcoes, interesse);
      setFiltros(nextFiltros);
      await load(nextFiltros, 1);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setLoading(false);
    }
  }, [interesse, load]);

  useEffect(() => {
    void bootstrap();
  }, [bootstrap]);

  function applySearch(value: string) {
    const next = { ...filtros, modeloContem: value.trim(), somenteInteresse: interesse };
    setFiltros(next);
    setSearch(value.trim());
    void load(next, 1);
  }

  function onSearchSubmit(e: FormEvent) {
    e.preventDefault();
    applySearch(search);
  }

  function goToPage(nextPage: number) {
    if (nextPage === page || nextPage < 1 || nextPage > maxPage) return;
    void load(filtros, nextPage).then((result) => {
      if (result) scrollToTop();
    });
  }

  function toggleInteresse(lote: Lote) {
    const nextFlag = !lote.interesse;
    setLotes((xs) =>
      xs.map((item) => (item.loteId === lote.loteId ? { ...item, interesse: nextFlag } : item)),
    );
    setDetail((d) => (d && d.loteId === lote.loteId ? { ...d, interesse: nextFlag } : d));
    setInteresseCount((n) => Math.max(0, n + (nextFlag ? 1 : -1)));
    void setInteresse(lote.loteId, nextFlag)
      .then(() => load(filtros, page))
      .then((result) => {
        if (!result) return;
        setDetail((d) => {
          if (!d) return null;
          return result.lotes.find((item) => item.loteId === d.loteId) ?? null;
        });
      });
  }

  return (
    <>
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
              setFiltros({ ...next, somenteInteresse: interesse });
              setDrawerOpen(false);
              void load(next, 1);
            }}
            onClear={() => {
              const next = baseFiltros(opcoes, interesse);
              setFiltros(next);
              setSearch("");
              setDrawerOpen(false);
              void load(next, 1);
            }}
          />
        </aside>
      )}

      <main className="main">
        <div className="main__inner">
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
                {compact && (
                  <button
                    type="button"
                    className="icon-btn"
                    aria-label="Filtros"
                    onClick={() => setDrawerOpen(true)}
                  >
                    <span className="material-symbols-outlined">tune</span>
                  </button>
                )}
                <h2>{fmtInt(total)} lotes</h2>
                {interesse ? (
                  <span className="chip">
                    <span className="material-icons">star</span>
                    {interesseCount} de interesse
                  </span>
                ) : (
                  <Link to="/interesse" className="chip chip--link">
                    <span className="material-icons">star</span>
                    {interesseCount} de interesse
                  </Link>
                )}
                {!compact && (
                  <form className="toolbar__search" onSubmit={onSearchSubmit}>
                    <span className="material-symbols-outlined">search</span>
                    <input
                      value={search}
                      placeholder="Modelo contém"
                      onChange={(e) => setSearch(e.target.value)}
                    />
                  </form>
                )}
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
                {loading && <span className="spinner" aria-label="Carregando" />}
              </div>
              <Pager page={page} maxPage={maxPage} onPage={goToPage} label="Paginação superior" />
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
                      onToggle={() => toggleInteresse(lote)}
                    />
                  ))}
                </div>
              )}
              <Pager page={page} maxPage={maxPage} onPage={goToPage} label="Paginação inferior" />
            </>
          )}
        </div>
      </main>

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

      {detail && (
        <LoteDetailDialog
          lote={detail}
          onClose={() => setDetail(null)}
          onToggle={() => toggleInteresse(detail)}
        />
      )}
    </>
  );
}
