import { pageWindow } from "./pageWindow";

type Props = {
  page: number;
  maxPage: number;
  onPage: (page: number) => void;
  label?: string;
};

export function Pager({ page, maxPage, onPage, label = "Paginação" }: Props) {
  if (maxPage <= 1) return null;
  const items = pageWindow(page, maxPage);
  return (
    <nav className="pager" aria-label={label}>
      <button
        type="button"
        className="icon-btn icon-btn--tonal"
        disabled={page <= 1}
        aria-label="Primeira página"
        onClick={() => onPage(1)}
      >
        <span className="material-symbols-outlined">first_page</span>
      </button>
      <button
        type="button"
        className="icon-btn icon-btn--tonal"
        disabled={page <= 1}
        aria-label="Página anterior"
        onClick={() => onPage(page - 1)}
      >
        <span className="material-symbols-outlined">chevron_left</span>
      </button>
      {items.map((item, i) =>
        item === "ellipsis" ? (
          <span key={`e${i}`} className="pager__ellipsis" aria-hidden>
            …
          </span>
        ) : (
          <button
            key={item}
            type="button"
            className={item === page ? "pager__num pager__num--current" : "pager__num"}
            aria-label={`Página ${item}`}
            aria-current={item === page ? "page" : undefined}
            onClick={() => onPage(item)}
          >
            {item}
          </button>
        ),
      )}
      <button
        type="button"
        className="icon-btn icon-btn--tonal"
        disabled={page >= maxPage}
        aria-label="Próxima página"
        onClick={() => onPage(page + 1)}
      >
        <span className="material-symbols-outlined">chevron_right</span>
      </button>
      <button
        type="button"
        className="icon-btn icon-btn--tonal"
        disabled={page >= maxPage}
        aria-label="Última página"
        onClick={() => onPage(maxPage)}
      >
        <span className="material-symbols-outlined">last_page</span>
      </button>
    </nav>
  );
}
