import { Link, NavLink, Route, Routes } from "react-router-dom";
import { AppErrorBoundary } from "./components/AppErrorBoundary";
import { TeamsProvider } from "./context/TeamsContext";
import { DataReviewPage } from "./pages/DataReviewPage";
import { HomePage } from "./pages/HomePage";
import { MatchDetailPage } from "./pages/MatchDetailPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { SimulatorPage } from "./pages/SimulatorPage";
import { TeamPage } from "./pages/TeamPage";
import { TeamsPage } from "./pages/TeamsPage";
import { TournamentPage } from "./pages/TournamentPage";

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  `relative whitespace-nowrap px-2 py-2 text-xs font-semibold transition sm:px-3 sm:text-sm ${
    isActive
      ? "text-emerald-300 after:absolute after:inset-x-2 after:-bottom-[13px] after:h-[3px] after:rounded-t-full after:bg-emerald-400 sm:after:inset-x-3"
      : "text-slate-400 hover:text-slate-100"
  }`;

function App() {
  return (
    <TeamsProvider>
      <div className="stadium-bg min-h-screen text-slate-100">
        {/* ピッチグリーンのトップライン */}
        <div className="h-[3px] bg-gradient-to-r from-emerald-600 via-emerald-400 to-emerald-600" />
        <header className="sticky top-0 z-40 border-b border-slate-700/70 bg-slate-950/85 backdrop-blur">
          <div className="mx-auto flex max-w-6xl items-center justify-between gap-2 px-4 py-3">
            <Link to="/" className="group flex shrink-0 items-center gap-2 whitespace-nowrap">
              <span className="score-num flex h-8 w-8 items-center justify-center rounded-md bg-gradient-to-b from-emerald-500 to-emerald-700 text-sm text-white shadow-[0_4px_12px_-4px_rgba(31,179,94,0.6)]">
                26
              </span>
              <span className="font-display text-lg font-extrabold tracking-wide">
                <span className="text-emerald-400">WC</span>
                <span className="text-slate-100">2026</span>
                <span className="ml-1.5 hidden align-middle text-xs font-bold tracking-widest text-slate-500 sm:inline">
                  SIMULATOR
                </span>
              </span>
            </Link>
            <nav className="flex min-w-0 gap-1 overflow-x-auto sm:gap-2">
              <NavLink to="/tournament" className={navLinkClass}>
                大会モード
              </NavLink>
              <NavLink to="/simulate" className={navLinkClass}>
                試合シミュレーター
              </NavLink>
              <NavLink to="/teams" className={navLinkClass}>
                チーム一覧
              </NavLink>
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-6xl px-4 py-6">
          <AppErrorBoundary>
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/tournament" element={<TournamentPage />} />
              <Route path="/simulate" element={<SimulatorPage />} />
              <Route path="/teams" element={<TeamsPage />} />
              <Route path="/matches/:matchId" element={<MatchDetailPage />} />
              <Route path="/teams/:teamId" element={<TeamPage />} />
              <Route path="/data-review" element={<DataReviewPage />} />
              <Route path="*" element={<NotFoundPage />} />
            </Routes>
          </AppErrorBoundary>
        </main>
        <footer className="mt-10 border-t border-slate-800 py-6 text-center text-xs text-slate-600">
          WC2026 シミュレーター — Poissonモデル × 実結果データによる非公式予測
        </footer>
      </div>
    </TeamsProvider>
  );
}

export default App;
