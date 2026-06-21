import { Link, NavLink, Route, Routes } from "react-router-dom";
import { TeamsProvider } from "./context/TeamsContext";
import { HomePage } from "./pages/HomePage";
import { MatchDetailPage } from "./pages/MatchDetailPage";
import { SimulatorPage } from "./pages/SimulatorPage";
import { TournamentPage } from "./pages/TournamentPage";

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  `whitespace-nowrap rounded-md px-2 py-1.5 text-xs font-medium transition sm:px-3 sm:text-sm ${
    isActive ? "bg-emerald-600 text-white" : "text-slate-300 hover:bg-slate-700 hover:text-white"
  }`;

function App() {
  return (
    <TeamsProvider>
      <div className="min-h-screen bg-slate-900 text-slate-100">
        <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur">
          <div className="mx-auto flex max-w-6xl items-center justify-between gap-2 px-4 py-3">
            <Link to="/" className="whitespace-nowrap text-base font-bold tracking-tight sm:text-lg">
              <span className="text-emerald-400">WC</span>2026
              <span className="hidden sm:inline"> シミュレーター</span>
            </Link>
            <nav className="flex gap-1 sm:gap-2">
              <NavLink to="/tournament" className={navLinkClass}>
                大会モード
              </NavLink>
              <NavLink to="/simulate" className={navLinkClass}>
                試合シミュレーター
              </NavLink>
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-6xl px-4 py-6">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/tournament" element={<TournamentPage />} />
            <Route path="/simulate" element={<SimulatorPage />} />
            <Route path="/matches/:matchId" element={<MatchDetailPage />} />
          </Routes>
        </main>
      </div>
    </TeamsProvider>
  );
}

export default App;
