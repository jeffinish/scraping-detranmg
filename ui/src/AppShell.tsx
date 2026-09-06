import { useState } from "react";
import { NavLink, Outlet } from "react-router";
import { useCompact } from "./useCompact";

const NAV = [
  { to: "/", label: "Home", icon: "home", end: true },
  { to: "/lotes", label: "Busca de lotes", icon: "search", end: false },
  { to: "/interesse", label: "Lotes de interesse", icon: "star", end: false },
] as const;

export function AppShell() {
  const compact = useCompact();
  const [navOpen, setNavOpen] = useState(false);

  const nav = (
    <nav className={compact ? "sidenav sidenav--modal" : "sidenav"} aria-label="Seções">
      {NAV.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.end}
          className={({ isActive }) => (isActive ? "sidenav__item sidenav__item--active" : "sidenav__item")}
          onClick={() => setNavOpen(false)}
        >
          <span className="material-symbols-outlined">{item.icon}</span>
          {item.label}
        </NavLink>
      ))}
      <span className="sidenav__item sidenav__item--soon" title="Em breve">
        <span className="material-symbols-outlined">monitoring</span>
        Analytics
        <small>em breve</small>
      </span>
    </nav>
  );

  return (
    <div className="shell">
      <header className={compact ? "topbar" : "topbar topbar--wide"}>
        {compact && (
          <button type="button" className="icon-btn" aria-label="Menu" onClick={() => setNavOpen(true)}>
            <span className="material-symbols-outlined">menu</span>
          </button>
        )}
        <div className="brand">
          <p className="brand__title">DETRAN/MG</p>
          <p className="brand__sub">Leilões</p>
        </div>
      </header>
      <div className="layout">
        {compact && navOpen && (
          <button type="button" className="scrim" aria-label="Fechar menu" onClick={() => setNavOpen(false)} />
        )}
        {(!compact || navOpen) && nav}
        <Outlet />
      </div>
    </div>
  );
}
