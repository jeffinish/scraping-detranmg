import { useEffect, useState } from "react";
import { tituloLote, type Lote } from "./types";
import { fetchLoteImagens, type LoteImagemSlot } from "./api";
import { InteresseButton, LoteSummary } from "./LoteSummary";
import "./LoteDetailDialog.css";

type Props = {
  lote: Lote;
  onClose: () => void;
  onToggle: () => void;
};

export function LoteDetailDialog({ lote, onClose, onToggle }: Props) {
  const linhas: [string, string][] = [
    ["Edital", lote.numeroEdital],
    ["Pátio", lote.patio],
    ["Encerramento", lote.dataEncerramento],
  ];
  const [slots, setSlots] = useState<LoteImagemSlot[] | null>(null);
  const [idx, setIdx] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setSlots(null);
    setIdx(0);
    fetchLoteImagens(lote.loteId)
      .then((next) => {
        if (!cancelled) setSlots(next);
      })
      .catch(() => {
        if (!cancelled) setSlots([]);
      });
    return () => {
      cancelled = true;
    };
  }, [lote.loteId]);

  const n = slots?.length ?? 0;
  const current = slots && n > 0 ? slots[Math.min(idx, n - 1)] : null;

  useEffect(() => {
    if (n <= 1) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "ArrowLeft") {
        event.preventDefault();
        setIdx((i) => (i - 1 + n) % n);
      } else if (event.key === "ArrowRight") {
        event.preventDefault();
        setIdx((i) => (i + 1) % n);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [n]);

  return (
    <div className="dialog-backdrop" onClick={onClose}>
      <div className="detail" role="dialog" aria-labelledby="detail-title" onClick={(e) => e.stopPropagation()}>
        <div className={`detail__media${current ? "" : " detail__media--empty"}`}>
          {current ? (
            <img
              src={current.url}
              alt=""
              onError={(e) => {
                e.currentTarget.style.display = "none";
              }}
            />
          ) : slots === null ? (
            <span className="detail__media-status">Carregando fotos…</span>
          ) : (
            <span className="material-symbols-outlined detail__fallback">directions_car</span>
          )}
          {n > 1 && current ? (
            <>
              <button
                type="button"
                className="detail__nav detail__nav--prev"
                aria-label="Foto anterior"
                onClick={() => setIdx((i) => (i - 1 + n) % n)}
              >
                <span className="material-symbols-outlined">chevron_left</span>
              </button>
              <button
                type="button"
                className="detail__nav detail__nav--next"
                aria-label="Próxima foto"
                onClick={() => setIdx((i) => (i + 1) % n)}
              >
                <span className="material-symbols-outlined">chevron_right</span>
              </button>
              <span className="detail__count">
                {Math.min(idx, n - 1) + 1}/{n}
              </span>
            </>
          ) : null}
        </div>
        <div className="detail__body">
          <div className="detail__title-row">
            <h2 id="detail-title">{tituloLote(lote)}</h2>
            <InteresseButton flagged={lote.interesse} onToggle={onToggle} />
          </div>
          <LoteSummary lote={lote} />
          {linhas.map(([label, value]) => (
            <div key={label} className="detail__row">
              <span>{label}</span>
              <strong>{value || "—"}</strong>
            </div>
          ))}
          <div className="detail__actions">
            <a className="btn btn--text" href={lote.urlDetalhes} target="_blank" rel="noreferrer">
              Abrir no portal
            </a>
            <button type="button" className="btn btn--filled" onClick={onClose}>
              Fechar
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
