import { tituloLote, type Lote } from "./types";
import { imageUrl } from "./api";
import "./LoteDetailDialog.css";

type Props = {
  lote: Lote;
  onClose: () => void;
};

export function LoteDetailDialog({ lote, onClose }: Props) {
  const linhas: [string, string][] = [
    ["Marca", lote.marca || "—"],
    ["Ano", lote.anoVeiculo],
    ["Valor", lote.valorFmt],
    ["Lote", lote.numeroLote],
    ["Edital", lote.numeroEdital],
    ["Município", lote.municipio],
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
          <h2 id="detail-title">{tituloLote(lote)}</h2>
          <div className="chips">
            <span className="chip">{lote.condicao}</span>
            <span className="chip">{lote.statusEdital}</span>
          </div>
          {linhas.map(([label, value]) => (
            <div key={label} className="detail__row">
              <span>{label}</span>
              <strong>{value}</strong>
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
