import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import { BracketView } from "../components/BracketView";
import { GroupStandingsGrid } from "../components/GroupStandingsGrid";
import type { TournamentResult } from "../types/domain";

export function TournamentPage() {
  const [result, setResult] = useState<TournamentResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [restoring, setRestoring] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // Once the user has triggered a run, a slow-resolving restore fetch from
  // mount must not clobber the fresh result with now-deleted match ids.
  const userHasRunRef = useRef(false);

  useEffect(() => {
    api
      .getTournamentState()
      .then((data) => {
        if (!userHasRunRef.current) setResult(data);
      })
      .catch((e) => setError(String(e)))
      .finally(() => setRestoring(false));
  }, []);

  async function runTournament() {
    userHasRunRef.current = true;
    setLoading(true);
    setError(null);
    try {
      const data = await api.runTournament();
      setResult(data);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  function resetTournament() {
    userHasRunRef.current = true;
    setResult(null);
    setError(null);
  }

  return (
    <div className="space-y-8">
      <section className="rounded-xl border border-slate-700 bg-slate-800/40 p-5">
        <h2 className="text-xl font-bold">大会モード</h2>
        <p className="mt-1 text-sm text-slate-400">
          ボタン一つでグループステージから決勝までの全104試合をシミュレーションします。各試合カードをクリックすると詳細なリプレイとデータを確認できます。
        </p>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button
            onClick={runTournament}
            disabled={loading || restoring}
            className="rounded-lg bg-emerald-600 px-5 py-2.5 font-semibold text-white shadow transition hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? "シミュレーション中..." : result ? "もう一度シミュレーション" : "大会を一括シミュレーション"}
          </button>
          {result && !loading && (
            <button
              onClick={resetTournament}
              className="rounded-lg border border-slate-600 px-4 py-2.5 text-sm font-medium text-slate-300 hover:bg-slate-700"
            >
              リセット
            </button>
          )}
        </div>
        {error && <p className="mt-3 text-sm text-rose-400">{error}</p>}
      </section>

      {restoring && <p className="text-sm text-slate-400">読み込み中...</p>}

      {!restoring && !result && !loading && (
        <p className="text-sm text-slate-400">まだ大会が実行されていません。上のボタンから開始してください。</p>
      )}

      {result && (
        // While a new run is in flight, the server briefly clears matches before
        // rewriting them — disable interaction so stale match links can't 404.
        <div className={loading ? "pointer-events-none opacity-40 transition-opacity" : "transition-opacity"}>
          <section>
            <h3 className="mb-3 text-lg font-bold">決勝トーナメント</h3>
            <BracketView result={result} />
          </section>
          <section className="mt-8">
            <h3 className="mb-3 text-lg font-bold">グループステージ順位表</h3>
            <GroupStandingsGrid groupStandings={result.group_standings} groupMatches={result.matches.group} />
          </section>
        </div>
      )}
    </div>
  );
}
