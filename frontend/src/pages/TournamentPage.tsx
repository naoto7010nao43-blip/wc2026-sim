import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import { BracketView } from "../components/BracketView";
import { GroupDifficultyPanel } from "../components/GroupDifficultyPanel";
import { GroupStandingsGrid } from "../components/GroupStandingsGrid";
import { TournamentHighlightsPanel } from "../components/TournamentHighlightsPanel";
import { TournamentDarkHorsesPanel } from "../components/TournamentDarkHorsesPanel";
import { TournamentFinalMatchupsPanel } from "../components/TournamentFinalMatchupsPanel";
import { TournamentGroupAdvancementPanel } from "../components/TournamentGroupAdvancementPanel";
import { TournamentOddsPanel } from "../components/TournamentOddsPanel";
import { TournamentPathProjectionPanel } from "../components/TournamentPathProjectionPanel";
import { TournamentUpsetWatchPanel } from "../components/TournamentUpsetWatchPanel";
import type { DataQualitySummary, TournamentResult } from "../types/domain";

type TabId = "result" | "odds" | "analysis";

const TABS: { id: TabId; label: string }[] = [
  { id: "result", label: "大会結果" },
  { id: "odds", label: "優勝予測" },
  { id: "analysis", label: "グループ分析" },
];

export function TournamentPage() {
  const [result, setResult] = useState<TournamentResult | null>(null);
  const [dataQuality, setDataQuality] = useState<DataQualitySummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [restoring, setRestoring] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>("result");
  // Once the user has triggered a run, a slow-resolving restore fetch from
  // mount must not clobber the fresh result with now-deleted match ids.
  const userHasRunRef = useRef(false);
  const tabsRef = useRef<HTMLDivElement | null>(null);

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
      setActiveTab("result");
      tabsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
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
    <div className="space-y-5">
      {/* ヘッダー: 実行ボタンまで(コンパクト化) */}
      <section className="panel fade-up p-5 sm:p-6">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="font-display text-[11px] font-bold uppercase tracking-[0.3em] text-emerald-400">Tournament Mode</p>
            <h2 className="mt-1 font-display text-2xl font-extrabold tracking-wide">大会モード</h2>
            <p className="mt-1 max-w-xl text-sm text-slate-400">
              グループステージから決勝までの全104試合を一括シミュレーション。試合カードをクリックすると詳細を確認できます。
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <button onClick={runTournament} disabled={loading || restoring} className="btn-primary px-6 py-2.5">
              {loading ? "シミュレーション中..." : result ? "もう一度シミュレーション" : "大会を一括シミュレーション"}
            </button>
            {result && !loading && (
              <button onClick={resetTournament} className="btn-secondary px-4 py-2.5 text-sm">
                リセット
              </button>
            )}
          </div>
        </div>
        {error && <p className="mt-3 text-sm text-rose-400">{error}</p>}

        {/* データ状態は折りたたみに格納してスクロール量を削減 */}
        <details className="group mt-4 border-t border-slate-700/80 pt-3">
          <summary className="flex cursor-pointer list-none items-center gap-2 text-xs font-semibold text-slate-500 transition hover:text-slate-300 [&::-webkit-details-marker]:hidden">
            <span aria-hidden className="text-emerald-500 transition group-open:rotate-90">▸</span>
            大会実行前のデータ状態を表示
          </summary>
          <TournamentReadinessStrip dataQuality={dataQuality} />
        </details>
      </section>

      {/* タブナビゲーション(スクロール後もヘッダー直下に固定) */}
      <div ref={tabsRef} className="sticky top-[57px] z-30 -mx-4 scroll-mt-[57px] border-b border-slate-700/70 bg-slate-950/90 px-4 backdrop-blur">
        <nav className="flex gap-1" role="tablist" aria-label="大会モードの表示切替">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              role="tab"
              aria-selected={activeTab === tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`relative px-4 py-2.5 text-sm font-semibold transition ${
                activeTab === tab.id
                  ? "text-emerald-300 after:absolute after:inset-x-3 after:bottom-0 after:h-[3px] after:rounded-t-full after:bg-emerald-400"
                  : "text-slate-400 hover:text-slate-100"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* タブ1: 大会結果 */}
      <div className={activeTab === "result" ? "space-y-8" : "hidden"}>
        {restoring && <p className="text-sm text-slate-400">読み込み中...</p>}

        {!restoring && !result && !loading && (
          <div className="panel flex flex-col items-center gap-3 p-10 text-center">
            <p className="score-num text-4xl text-slate-600">0 – 0</p>
            <p className="text-sm text-slate-400">まだ大会が実行されていません。</p>
            <p className="text-xs text-slate-500">上の「大会を一括シミュレーション」から開始してください。</p>
          </div>
        )}

        {result && (
          // While a new run is in flight, the server briefly clears matches before
          // rewriting them; disable interaction so stale match links can't 404.
          <div className={loading ? "pointer-events-none space-y-8 opacity-40 transition-opacity" : "space-y-8 transition-opacity"}>
            <TournamentHighlightsPanel result={result} />
            <section>
              <h3 className="mb-3 flex items-center gap-2 font-display text-xl font-extrabold tracking-wide">
                <span className="h-5 w-1 rounded-full bg-emerald-400" />
                決勝トーナメント
              </h3>
              <BracketView result={result} />
            </section>
            <section>
              <h3 className="mb-3 flex items-center gap-2 font-display text-xl font-extrabold tracking-wide">
                <span className="h-5 w-1 rounded-full bg-emerald-400" />
                グループステージ順位表
              </h3>
              <GroupStandingsGrid groupStandings={result.group_standings} groupMatches={result.matches.group} />
            </section>
          </div>
        )}
      </div>

      {/* タブ2: 優勝予測(hiddenで保持し、再フェッチを防ぐ) */}
      <div className={activeTab === "odds" ? "space-y-8" : "hidden"}>
        <TournamentOddsPanel />
        <TournamentFinalMatchupsPanel />
        <TournamentDarkHorsesPanel />
      </div>

      {/* タブ3: グループ分析 */}
      <div className={activeTab === "analysis" ? "space-y-8" : "hidden"}>
        <TournamentGroupAdvancementPanel />
        <GroupDifficultyPanel />
        <TournamentPathProjectionPanel />
        <TournamentUpsetWatchPanel />
      </div>
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
    <div className="pt-1">
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
