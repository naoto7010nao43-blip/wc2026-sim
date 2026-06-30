import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import { BracketView } from "../components/BracketView";
import { GroupStandingsGrid } from "../components/GroupStandingsGrid";
import { TournamentHighlightsPanel } from "../components/TournamentHighlightsPanel";
import { TournamentOddsPanel } from "../components/TournamentOddsPanel";
import type { DataQualitySummary, TournamentResult } from "../types/domain";

export function TournamentPage() {
  const [result, setResult] = useState<TournamentResult | null>(null);
  const [dataQuality, setDataQuality] = useState<DataQualitySummary | null>(null);
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

  useEffect(() => {
    let cancelled = false;
    api
      .getDataQualitySummary()
      .then((data) => {
        if (!cancelled) setDataQuality(data);
      })
      .catch(() => {
        if (!cancelled) setDataQuality(null);
      });
    return () => {
      cancelled = true;
    };
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
          ボタンひとつでグループステージから決勝までの全104試合をシミュレーションします。
          各試合カードをクリックすると、詳細なリプレイとデータを確認できます。
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
        <TournamentReadinessStrip dataQuality={dataQuality} />
      </section>

      <TournamentOddsPanel />

      {restoring && <p className="text-sm text-slate-400">読み込み中...</p>}

      {!restoring && !result && !loading && (
        <p className="text-sm text-slate-400">まだ大会が実行されていません。上のボタンから開始してください。</p>
      )}

      {result && (
        // While a new run is in flight, the server briefly clears matches before
        // rewriting them; disable interaction so stale match links can't 404.
        <div className={loading ? "pointer-events-none space-y-8 opacity-40 transition-opacity" : "space-y-8 transition-opacity"}>
          <TournamentHighlightsPanel result={result} />
          <section>
            <h3 className="mb-3 text-lg font-bold">決勝トーナメント</h3>
            <BracketView result={result} />
          </section>
          <section>
            <h3 className="mb-3 text-lg font-bold">グループステージ順位表</h3>
            <GroupStandingsGrid groupStandings={result.group_standings} groupMatches={result.matches.group} />
          </section>
        </div>
      )}
    </div>
  );
}

function TournamentReadinessStrip({ dataQuality }: { dataQuality: DataQualitySummary | null }) {
  const groupCoverage =
    dataQuality && dataQuality.real_group_match_expected > 0
      ? `${dataQuality.real_group_match_count}/${dataQuality.real_group_match_expected}試合`
      : "確認中";
  const officialCoverage = dataQuality ? `${dataQuality.official_profile_coverage_pct.toFixed(1)}%` : "確認中";
  const unmatchedSeedPlayers =
    dataQuality?.remaining_unmatched_seed_players == null ? "確認中" : `${dataQuality.remaining_unmatched_seed_players}人`;
  const knockoutMatches = dataQuality?.real_knockout_match_count == null ? "確認中" : `${dataQuality.real_knockout_match_count}試合`;
  const freshnessStatus =
    dataQuality?.freshness_status === "critical" ? "再確認推奨" : dataQuality?.freshness_status === "warning" ? "一部注意" : "良好";

  return (
    <div className="mt-5 border-t border-slate-700/80 pt-4">
      <p className="text-xs font-semibold uppercase tracking-widest text-slate-500">大会実行前のデータ状態</p>
      <dl className="mt-3 grid grid-cols-2 gap-x-5 gap-y-3 text-sm md:grid-cols-4">
        <StatusMetric label="実結果反映" value={groupCoverage} detail={`決勝T ${knockoutMatches}`} />
        <StatusMetric label="公式プロフィール" value={officialCoverage} detail="選手属性の反映率" />
        <StatusMetric label="未対応シード選手" value={unmatchedSeedPlayers} detail="今後の確認対象" />
        <StatusMetric label="鮮度確認" value={dataQuality ? freshnessStatus : "確認中"} detail="再確認対象の有無" />
      </dl>
      <p className="mt-3 max-w-3xl text-xs leading-relaxed text-slate-500">
        実施済みの試合結果は固定し、未実施カードは現在のPoissonモデルで予測します。数値が近いチーム同士は、順位より候補帯として見るのが自然です。
      </p>
    </div>
  );
}

function StatusMetric({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <div className="min-w-0">
      <dt className="truncate text-xs text-slate-500">{label}</dt>
      <dd className="mt-1 text-base font-bold text-slate-100">{value}</dd>
      <dd className="mt-0.5 truncate text-xs text-slate-500">{detail}</dd>
    </div>
  );
}
