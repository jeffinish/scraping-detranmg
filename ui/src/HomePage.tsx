import { Link } from "react-router";

export function HomePage() {
  return (
    <main className="main">
      <div className="main__inner home">
        <h2>Home</h2>
        <p>Acompanhamento local dos leilões do DETRAN/MG.</p>
        <div className="home__actions">
          <Link to="/lotes" className="btn btn--filled">
            Busca de lotes
          </Link>
          <Link to="/interesse" className="btn btn--tonal">
            Lotes de interesse
          </Link>
        </div>
        <p className="home__hint">
          Analytics (totais, lotes por status) entra numa próxima iteração.
        </p>
      </div>
    </main>
  );
}
