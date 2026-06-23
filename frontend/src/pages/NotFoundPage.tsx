import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <div className="mx-auto max-w-2xl rounded-lg border border-slate-700 bg-slate-800/40 p-6 text-center">
      <p className="text-xs uppercase tracking-widest text-slate-500">404</p>
      <h2 className="mt-2 text-xl font-bold text-slate-100">ページが見つかりません</h2>
      <p className="mt-2 text-sm text-slate-400">
        URLが変更されたか、対象の試合・チームが存在しない可能性があります。
      </p>
      <div className="mt-5 flex flex-wrap justify-center gap-3">
        <Link to="/tournament" className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-500">
          大会モード
        </Link>
        <Link to="/simulate" className="rounded-md border border-slate-600 px-4 py-2 text-sm font-semibold text-slate-200 hover:bg-slate-700">
          試合シミュレーター
        </Link>
        <Link to="/teams" className="rounded-md border border-slate-600 px-4 py-2 text-sm font-semibold text-slate-200 hover:bg-slate-700">
          チーム一覧
        </Link>
      </div>
    </div>
  );
}

