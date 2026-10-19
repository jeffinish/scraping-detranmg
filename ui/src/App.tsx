import { Route, Routes } from "react-router";
import { AppShell } from "./AppShell";
import { AnalyticsPage } from "./AnalyticsPage";
import { HomePage } from "./HomePage";
import { LotesPage } from "./LotesPage";
import "./App.css";

export function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route path="/" element={<HomePage />} />
        <Route path="/analytics" element={<AnalyticsPage />} />
        <Route path="/lotes" element={<LotesPage key="lotes" />} />
        <Route path="/interesse" element={<LotesPage key="interesse" interesse />} />
      </Route>
    </Routes>
  );
}
