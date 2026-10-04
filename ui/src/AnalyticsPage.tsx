import { useEffect, useState } from "react";
import { Link } from "react-router";
import { fetchAnalytics, type Analytics, type AnalyticsEdital, type AnalyticsMunicipio } from "./api";

function fmtInt(value: number): string {
  return value.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ".");
}

function busca(params: Record<string, string>) {
  return { pathname: "/lotes", search: `?${new URLSearchParams(params).toString()}` };
}

export function AnalyticsPage() {
  const [data, setData] = useState<Analytics | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancel = false;
    fetchAnalytics()
      .then((next) => {
        if (!cancel) setData(next);
      })
      .catch((e: unknown) => {
        if (!cancel) setError(e instanceof Error ? e.message : String(e));
      });
    return () => {
      cancel = true;
    };
  }, []);

  return (
    <main className="main">
      <div className="main__inner analytics">
        <h2>Analytics</h2>
        <p>Lotes ativos em editais Publicado ou Em Andamento.</p>
        {error ? (
          <div className="error">
            <span className="material-symbols-outlined">cloud_off</span>
            <h2>Banco indisponível</h2>
            <p>{error}</p>
          </div>
        ) : data == null ? (
          <span className="spinner" aria-label="Carregando" />
        ) : (
          <>
            <section>
              <h3>Lotes por município</h3>
              <div className="analytics__scroll">
                <table className="analytics__table">
                  <thead>
                    <tr>
                      <th>Município</th>
                      <th className="analytics__num">Veículos</th>
                      <th className="analytics__num">Motos</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.municipios.map((row) => (
                      <MunicipioRow key={row.municipio} row={row} />
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
            <section>
              <h3>Editais</h3>
              <div className="analytics__scroll">
                <table className="analytics__table">
                  <thead>
                    <tr>
                      <th>Edital</th>
                      <th>Município</th>
                      <th>Status</th>
                      <th>Encerramento</th>
                      <th className="analytics__num">Veículos</th>
                      <th className="analytics__num">Motos</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.editais.map((row) => (
                      <EditalRow key={row.leilaoId} row={row} />
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          </>
        )}
      </div>
    </main>
  );
}

function MunicipioRow({ row }: { row: AnalyticsMunicipio }) {
  return (
    <tr>
      <td>{row.municipio}</td>
      <td className="analytics__num">
        <Link to={busca({ municipio: row.municipio, categoria: "veiculo" })}>{fmtInt(row.veiculo)}</Link>
      </td>
      <td className="analytics__num">
        <Link to={busca({ municipio: row.municipio, categoria: "moto" })}>{fmtInt(row.moto)}</Link>
      </td>
    </tr>
  );
}

function EditalRow({ row }: { row: AnalyticsEdital }) {
  const edital = { leilao_id: String(row.leilaoId) };
  return (
    <tr>
      <td>{row.numeroEdital}</td>
      <td>{row.municipio}</td>
      <td>{row.status}</td>
      <td>{row.dataEncerramento || "—"}</td>
      <td className="analytics__num">
        <Link to={busca({ ...edital, categoria: "veiculo" })}>{fmtInt(row.veiculo)}</Link>
      </td>
      <td className="analytics__num">
        <Link to={busca({ ...edital, categoria: "moto" })}>{fmtInt(row.moto)}</Link>
      </td>
    </tr>
  );
}
