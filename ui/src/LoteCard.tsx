import { tituloLote, type Lote } from "./types";
import { imageUrl } from "./api";
import { InteresseButton, LoteSummary } from "./LoteSummary";
import "./LoteCard.css";

type Props = {
  lote: Lote;
  onOpen: () => void;
  onToggle: () => void;
};

export function LoteCard({ lote, onOpen, onToggle }: Props) {
  return (
    <article className="card">
      <div className="card__media-wrap">
        <button type="button" className="card__media" onClick={onOpen}>
          <img
            src={imageUrl(lote.loteId)}
            alt=""
            onError={(e) => {
              e.currentTarget.style.display = "none";
              e.currentTarget.parentElement?.classList.add("card__media--empty");
            }}
          />
          <span className="material-symbols-outlined card__fallback">directions_car</span>
        </button>
        <InteresseButton flagged={lote.interesse} onToggle={onToggle} className="icon-btn card__star" />
      </div>
      <div className="card__body">
        <h3 className="card__title">{tituloLote(lote)}</h3>
        <LoteSummary lote={lote} />
      </div>
    </article>
  );
}
