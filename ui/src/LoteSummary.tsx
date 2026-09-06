import { type Lote } from "./types";
import "./LoteSummary.css";

export function LoteSummary({ lote }: { lote: Lote }) {
  return (
    <div className="lote-summary">
      <div className="chips">
        {lote.marca ? <span className="chip">{lote.marca}</span> : null}
        {lote.anoVeiculo !== "—" ? <span className="chip">{lote.anoVeiculo}</span> : null}
        <span className="chip">{lote.condicao}</span>
        <span className="chip">{lote.statusEdital}</span>
        {!lote.ativo ? <span className="chip">Inativo</span> : null}
        {!lote.editalAtivo ? <span className="chip">Edital inativo</span> : null}
      </div>
      <p className="lote-summary__price">{lote.valorFmt}</p>
      <p className="lote-summary__meta">
        {lote.municipio} · lote {lote.numeroLote}
      </p>
    </div>
  );
}

type InteresseProps = {
  flagged: boolean;
  onToggle: () => void;
  className?: string;
};

export function InteresseButton({ flagged, onToggle, className }: InteresseProps) {
  const label = flagged ? "Remover interesse" : "Marcar interesse";
  return (
    <button
      type="button"
      className={className ?? "icon-btn"}
      title={label}
      aria-label={label}
      aria-pressed={flagged}
      onClick={onToggle}
    >
      <span className={flagged ? "material-icons fill" : "material-icons"} aria-hidden="true">
        {flagged ? "star" : "star_border"}
      </span>
    </button>
  );
}
