import { useEffect, useMemo, useState } from "react";
import type { Filtros, Opcoes } from "./types";
import "./FilterPanel.css";

type Props = {
  filtros: Filtros;
  opcoes: Opcoes | null;
  onChange: (next: Filtros) => void;
  onApply: (next: Filtros) => void;
  onClear: () => void;
};

export function FilterPanel({ filtros, opcoes, onChange, onApply, onClear }: Props) {
  const [valorMin, setValorMin] = useState(num(filtros.valorMin));
  const [valorMax, setValorMax] = useState(num(filtros.valorMax));
  const [anoMin, setAnoMin] = useState(num(filtros.anoMin));
  const [anoMax, setAnoMax] = useState(num(filtros.anoMax));

  useEffect(() => {
    setValorMin(num(filtros.valorMin));
    setValorMax(num(filtros.valorMax));
    setAnoMin(num(filtros.anoMin));
    setAnoMax(num(filtros.anoMax));
  }, [filtros.valorMin, filtros.valorMax, filtros.anoMin, filtros.anoMax]);

  function syncNumbers(): Filtros {
    return {
      ...filtros,
      valorMin: parseFloatSafe(valorMin),
      valorMax: parseFloatSafe(valorMax),
      anoMin: parseIntSafe(anoMin),
      anoMax: parseIntSafe(anoMax),
    };
  }

  function aplicar() {
    const next = syncNumbers();
    onChange(next);
    onApply(next);
  }

  return (
    <div className="filters">
      <h2 className="filters__title">Filtros</h2>
      <MultiSelect
        label="Marca"
        options={opcoes?.marcas ?? []}
        selected={filtros.marcas}
        onChange={(marcas) => onChange({ ...filtros, marcas })}
      />
      <MultiSelect
        label="Município"
        options={opcoes?.municipios ?? []}
        selected={filtros.municipios}
        onChange={(municipios) => onChange({ ...filtros, municipios })}
      />
      <p className="filters__label">Condição</p>
      <ChipWrap
        options={opcoes?.condicoes ?? []}
        selected={filtros.condicoes}
        onChange={(condicoes) => onChange({ ...filtros, condicoes })}
      />
      <p className="filters__label">Status do edital</p>
      <ChipWrap
        options={opcoes?.statusEdital ?? []}
        selected={filtros.statusEdital}
        onChange={(statusEdital) => onChange({ ...filtros, statusEdital })}
      />
      <div className="filters__row">
        <label className="field">
          <span>Valor mín.</span>
          <input
            value={valorMin}
            inputMode="decimal"
            onChange={(e) => setValorMin(e.target.value.replace(/[^0-9.,]/g, ""))}
            onKeyDown={(e) => e.key === "Enter" && aplicar()}
          />
        </label>
        <label className="field">
          <span>Valor máx.</span>
          <input
            value={valorMax}
            inputMode="decimal"
            onChange={(e) => setValorMax(e.target.value.replace(/[^0-9.,]/g, ""))}
            onKeyDown={(e) => e.key === "Enter" && aplicar()}
          />
        </label>
      </div>
      <div className="filters__row">
        <label className="field">
          <span>Ano mín.</span>
          <input
            value={anoMin}
            inputMode="numeric"
            onChange={(e) => setAnoMin(e.target.value.replace(/\D/g, ""))}
            onKeyDown={(e) => e.key === "Enter" && aplicar()}
          />
        </label>
        <label className="field">
          <span>Ano máx.</span>
          <input
            value={anoMax}
            inputMode="numeric"
            onChange={(e) => setAnoMax(e.target.value.replace(/\D/g, ""))}
            onKeyDown={(e) => e.key === "Enter" && aplicar()}
          />
        </label>
      </div>
      <button type="button" className="btn btn--filled" onClick={aplicar}>
        <span className="material-symbols-outlined">filter_list</span>
        Aplicar
      </button>
      <button
        type="button"
        className="btn btn--text"
        onClick={() => {
          setValorMin("");
          setValorMax("");
          setAnoMin("");
          setAnoMax("");
          onClear();
        }}
      >
        <span className="material-symbols-outlined">filter_alt_off</span>
        Limpar
      </button>
    </div>
  );
}

function ChipWrap({
  options,
  selected,
  onChange,
}: {
  options: string[];
  selected: string[];
  onChange: (next: string[]) => void;
}) {
  return (
    <div className="chips">
      {options.map((option) => {
        const on = selected.includes(option);
        return (
          <button
            key={option}
            type="button"
            className={on ? "chip chip--selected" : "chip"}
            onClick={() =>
              onChange(on ? selected.filter((s) => s !== option) : [...selected, option])
            }
          >
            {option}
          </button>
        );
      })}
    </div>
  );
}

function MultiSelect({
  label,
  options,
  selected,
  onChange,
}: {
  label: string;
  options: string[];
  selected: string[];
  onChange: (next: string[]) => void;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [working, setWorking] = useState<string[]>(selected);

  const filtered = useMemo(() => {
    const q = query.toLowerCase();
    return options.filter((o) => !q || o.toLowerCase().includes(q));
  }, [options, query]);

  function openDialog() {
    setWorking(selected);
    setQuery("");
    setOpen(true);
  }

  return (
    <div className="multiselect">
      <button type="button" className="btn btn--outlined" onClick={openDialog}>
        <span className="material-symbols-outlined">tune</span>
        {label} ({selected.length})
      </button>
      {selected.length > 0 && (
        <div className="chips">
          {selected.map((item) => (
            <button
              key={item}
              type="button"
              className="chip chip--input"
              onClick={() => onChange(selected.filter((s) => s !== item))}
            >
              {item}
              <span className="material-symbols-outlined">close</span>
            </button>
          ))}
        </div>
      )}
      {open && (
        <div className="dialog-backdrop" onClick={() => setOpen(false)}>
          <div
            className="dialog"
            role="dialog"
            aria-labelledby={`ms-${label}`}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 id={`ms-${label}`}>{label}</h3>
            <label className="field">
              <span className="material-symbols-outlined">search</span>
              <input
                value={query}
                placeholder="Buscar"
                onChange={(e) => setQuery(e.target.value)}
                autoFocus
              />
            </label>
            <ul className="dialog__list">
              {filtered.map((option) => (
                <li key={option}>
                  <label className="check">
                    <input
                      type="checkbox"
                      checked={working.includes(option)}
                      onChange={(e) =>
                        setWorking(
                          e.target.checked
                            ? [...working, option]
                            : working.filter((v) => v !== option),
                        )
                      }
                    />
                    {option}
                  </label>
                </li>
              ))}
            </ul>
            <div className="dialog__actions">
              <button type="button" className="btn btn--text" onClick={() => setOpen(false)}>
                Cancelar
              </button>
              <button
                type="button"
                className="btn btn--filled"
                onClick={() => {
                  onChange(working);
                  setOpen(false);
                }}
              >
                Ok
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function num(value: number | null): string {
  return value == null ? "" : String(value);
}

function parseFloatSafe(value: string): number | null {
  const n = Number(value.replace(",", "."));
  return value.trim() && Number.isFinite(n) ? n : null;
}

function parseIntSafe(value: string): number | null {
  const n = Number.parseInt(value, 10);
  return value.trim() && Number.isFinite(n) ? n : null;
}
