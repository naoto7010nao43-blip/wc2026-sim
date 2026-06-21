import { Link } from "react-router-dom";

export function HomePage() {
  return (
    <div className="flex flex-col items-center gap-10 py-12 text-center">
      <div>
        <h1 className="text-4xl font-extrabold tracking-tight sm:text-5xl">
          <span className="text-emerald-400">WC</span>2026 シミュレーター
        </h1>
        <p className="mt-3 text-sm text-slate-400 sm:text-base">
          実際の試合結果と戦術データに基づく、2026 FIFAワールドカップ予測シミュレーター
        </p>
      </div>

      <div className="grid w-full max-w-3xl grid-cols-1 gap-5 sm:grid-cols-2">
        <Link
          to="/tournament"
          className="group rounded-2xl border border-slate-700 bg-slate-800/40 p-6 text-left transition hover:border-emerald-500 hover:bg-slate-800"
        >
          <div className="text-3xl">🏆</div>
          <h2 className="mt-3 text-lg font-bold text-slate-100 group-hover:text-emerald-400">大会モード</h2>
          <p className="mt-2 text-sm text-slate-400">
            グループステージから決勝まで、48チーム全104試合を一括シミュレーション。実際に行われた試合は実結果を反映します。
          </p>
        </Link>

        <Link
          to="/simulate"
          className="group rounded-2xl border border-slate-700 bg-slate-800/40 p-6 text-left transition hover:border-emerald-500 hover:bg-slate-800"
        >
          <div className="text-3xl">⚽</div>
          <h2 className="mt-3 text-lg font-bold text-slate-100 group-hover:text-emerald-400">試合シミュレーター</h2>
          <p className="mt-2 text-sm text-slate-400">
            気になる2チームを選んで、その1試合だけを詳細にシミュレーション。リプレイで戦況を確認できます。
          </p>
        </Link>
      </div>
    </div>
  );
}
