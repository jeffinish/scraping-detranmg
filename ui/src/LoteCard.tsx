import { tituloLote, type Lote } from "./types";
import { imageUrl } from "./api";
import "./LoteCard.css";

type Props = {
  lote: Lote;
  onOpen: () => void;
  onToggle: () => void;
};

export function LoteCard({ lote, onOpen, onToggle }: Props) {
  return (
    <article className="card">
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
      <div className="card__body">
        <div className="card__title-row">
          <h3 className="card__title">{tituloLote(lote)}</h3>
          <button
            type="button"
            className="icon-btn"
            title={lote.interesse ? "Remover interesse" : "Marcar interesse"}
            onClick={onToggle}
          >
            <span className={lote.interesse ? "material-symbols-outlined fill" : "material-symbols-outlined"}>
              star
            </span>
          </button>
        </div>
        <div className="chips">
          {lote.marca ? <span className="chip">{lote.marca}</span> : null}
          {lote.anoVeiculo !== "—" ? <span className="chip">{lote.anoVeiculo}</span> : null}
          <span className="chip">{lote.condicao}</span>
          <span className="chip">{lote.statusEdital}</span>
        </div>
        <p className="card__price">{lote.valorFmt}</p>
        <p className="card__meta">
          {lote.municipio} · lote {lote.numeroLote}
        </p>
      </div>
    </article>
  );
}
