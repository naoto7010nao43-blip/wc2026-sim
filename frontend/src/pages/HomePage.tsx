import { Link } from "react-router-dom";
import { DataQualityPanel } from "../components/DataQualityPanel";

export function HomePage() {
  return (
    <div className="flex flex-col items-center gap-10 py-10 text-center sm:py-14">
      {/* ヒーロー: センターサークルのピッチモチーフ */}
      <div className="relative w-full">
        <svg
          aria-hidden
          viewBox="0 0 600 260"
          className="pointer-events-none absolute left-1/2 top-1/2 -z-10 h-[300px] w-[640px] -translate-x-1/2 -translate-y-1/2 opacity-[0.16]"
        >
          <g fill="none" stroke="#34d26b" strokeWidth="1.5">
            <line x1="300" y1="0" x2="300" y2="260" />
            <circle cx="300" cy="130" r="78" />
            <circle cx="300" cy="130" r="3" fill="#34d26b" stroke="none" />
          </g>
        </svg>
        <p className="font-display text-xs font-bold uppercase tracking-[0.4em] text-emerald-400">
          FIFA World Cup 2026
        </p>
        <h1 className="mt-3 font-display text-5xl font-extrabold tracking-tight text-slate-100 sm:text-6xl">
          <span className="text-emerald-400">WC</span>2026 シミュレーター
        </h1>
        <p className="mx-auto mt-4 max-w-xl text-sm leading-relaxed text-slate-400 sm:text-base">
          実際の試合結果、公式スカッド情報、戦術データを組み合わせた
          <br className="hidden sm:block" />
          2026 FIFAワールドカップ予測シミュレーター
        </p>
        <div className="mt-5 flex flex-wrap items-center justify-center gap-2 text-[11px] text-slate-500">
          <span className="rounded-full border border-slate-700 bg-slate-800/60 px-3 py-1">48チーム</span>
          <span className="rounded-full border border-slate-700 bg-slate-800/60 px-3 py-1">全104試合</span>
          <span className="rounded-full border border-slate-700 bg-slate-800/60 px-3 py-1">Poissonモデル予測</span>
          <span className="rounded-full border border-amber-500/40 bg-amber-500/10 px-3 py-1 text-amber-300">実結果を反映</span>
        </div>
      </div>

      <div className="grid w-full max-w-3xl grid-cols-1 gap-5 sm:grid-cols-2">
        <ModeCard
          to="/tournament"
          mode="MODE 1"
          title="大会モード"
          description="グループステージから決勝まで、48チーム全104試合を一括シミュレーション。実際に行われた試合は実結果を反映します。"
        />
        <ModeCard
          to="/simulate"
          mode="MODE 2"
          title="試合シミュレーター"
          description="気になる2チームを選んで、その1試合だけを詳細にシミュレーション。事前予測とリプレイで戦況を確認できます。"
        />
      </div>

      <div className="w-full max-w-3xl">
        <DataQualityPanel />
      </div>
    </div>
  );
}

function ModeCard({ to, mode, title, description }: { to: string; mode: string; title: string; description: string }) {
  return (
    <Link
      to={to}
      className="group panel relative overflow-hidden p-6 text-left transition hover:border-emerald-500/70 hover:shadow-[0_10px_35px_-12px_rgba(31,179,94,0.35)]"
    >
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 h-[2px] bg-gradient-to-r from-transparent via-emerald-400/70 to-transparent opacity-0 transition group-hover:opacity-100"
      />
      <div className="font-display text-xs font-bold tracking-[0.25em] text-emerald-400">{mode}</div>
      <h2 className="mt-3 flex items-center gap-2 text-lg font-bold text-slate-100 transition group-hover:text-emerald-300">
        {title}
        <span aria-hidden className="translate-x-0 text-emerald-500 transition group-hover:translate-x-1">
          →
        </span>
      </h2>
      <p className="mt-2 text-sm leading-relaxed text-slate-400">{description}</p>
    </Link>
  );
}
