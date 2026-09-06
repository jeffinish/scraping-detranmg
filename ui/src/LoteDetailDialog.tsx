import { tituloLote, type Lote } from "./types";
import { imageUrl } from "./api";
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

  return (
    <div className="dialog-backdrop" onClick={onClose}>
      <div className="detail" role="dialog" aria-labelledby="detail-title" onClick={(e) => e.stopPropagation()}>
        <div className="detail__media">
          <img
            src={imageUrl(lote.loteId)}
            alt=""
            onError={(e) => {
              e.currentTarget.style.display = "none";
            }}
          />
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
