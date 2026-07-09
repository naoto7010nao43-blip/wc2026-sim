import { Link, NavLink, Route, Routes } from "react-router-dom";
import { AppErrorBoundary } from "./components/AppErrorBoundary";
import { TeamsProvider } from "./context/TeamsContext";
import { AccuracyPage } from "./pages/AccuracyPage";
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
            <nav className="hidden min-w-0 gap-2 sm:flex">
              <NavLink to="/tournament" className={navLinkClass}>
                大会モード
              </NavLink>
              <NavLink to="/simulate" className={navLinkClass}>
                試合シミュレーター
              </NavLink>
              <NavLink to="/teams" className={navLinkClass}>
                チーム一覧
              </NavLink>
              <NavLink to="/accuracy" className={navLinkClass}>
                的中実績
              </NavLink>
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-6xl px-4 py-6 pb-24 sm:pb-6">
          <AppErrorBoundary>
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/tournament" element={<TournamentPage />} />
              <Route path="/simulate" element={<SimulatorPage />} />
              <Route path="/teams" element={<TeamsPage />} />
              <Route path="/matches/:matchId" element={<MatchDetailPage />} />
              <Route path="/teams/:teamId" element={<TeamPage />} />
              <Route path="/accuracy" element={<AccuracyPage />} />
              <Route path="/data-review" element={<DataReviewPage />} />
              <Route path="*" element={<NotFoundPage />} />
            </Routes>
          </AppErrorBoundary>
        </main>
        <footer className="mt-10 border-t border-slate-800 py-6 pb-24 text-center text-xs text-slate-600 sm:pb-6">
          WC2026 シミュレーター — Poissonモデル × 実結果データによる非公式予測
        </footer>
        <MobileBottomNav />
      </div>
    </TeamsProvider>
  );
}

function MobileBottomNav() {
  const itemClass = ({ isActive }: { isActive: boolean }) =>
    `flex flex-col items-center justify-center gap-0.5 py-2 text-[10px] font-semibold transition ${
      isActive ? "text-emerald-300" : "text-slate-500"
    }`;
  return (
    <nav
      className="fixed inset-x-0 bottom-0 z-50 border-t border-slate-700/70 bg-slate-950/95 backdrop-blur sm:hidden"
      style={{ paddingBottom: "env(safe-area-inset-bottom)" }}
      aria-label="メインナビゲーション"
    >
      <div className="grid grid-cols-5">
        <NavLink to="/" end className={itemClass}>
          <HomeIcon />
          ホーム
        </NavLink>
        <NavLink to="/tournament" className={itemClass}>
          <TrophyIcon />
          大会
        </NavLink>
        <NavLink to="/simulate" className={itemClass}>
          <BoltIcon />
          シミュ
        </NavLink>
        <NavLink to="/teams" className={itemClass}>
          <FlagIcon />
          チーム
        </NavLink>
        <NavLink to="/accuracy" className={itemClass}>
          <TargetIcon />
          的中
        </NavLink>
      </div>
    </nav>
  );
}

const iconProps = {
  width: 22,
  height: 22,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 2,
  strokeLinecap: "round",
  strokeLinejoin: "round",
} as const;

function HomeIcon() {
  return (
    <svg {...iconProps} aria-hidden>
      <path d="M3 10.5 12 3l9 7.5" />
      <path d="M5 9.5V21h14V9.5" />
    </svg>
  );
}

function TrophyIcon() {
  return (
    <svg {...iconProps} aria-hidden>
      <path d="M8 21h8M12 17v4M7 4h10v5a5 5 0 0 1-10 0V4Z" />
      <path d="M7 6H4a3 3 0 0 0 3 5M17 6h3a3 3 0 0 1-3 5" />
    </svg>
  );
}

function BoltIcon() {
  return (
    <svg {...iconProps} aria-hidden>
      <path d="M13 2 4 14h6l-1 8 9-12h-6l1-8Z" />
    </svg>
  );
}

function FlagIcon() {
  return (
    <svg {...iconProps} aria-hidden>
      <path d="M5 21V4" />
      <path d="M5 4c4-2 8 2 14 0v9c-6 2-10-2-14 0" />
    </svg>
  );
}

function TargetIcon() {
  return (
    <svg {...iconProps} aria-hidden>
      <circle cx="12" cy="12" r="9" />
      <circle cx="12" cy="12" r="5" />
      <circle cx="12" cy="12" r="1" />
    </svg>
  );
}

export default App;
