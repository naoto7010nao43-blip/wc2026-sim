import { useEffect, useState } from "react";
import { api } from "../api/client";
import { ManagerTacticalTrustPanel } from "../components/ManagerTacticalTrustPanel";
import { RatingReviewWorkbenchPanel } from "../components/RatingReviewWorkbenchPanel";
import { SquadGapPanel } from "../components/SquadGapPanel";
import { TeamDataReviewPanel } from "../components/TeamDataReviewPanel";
import type {
  ManagerTacticalTrustSummary,
  RatingReviewWorkbenchSummary,
  SquadGapSummary,
  TeamReviewSummary,
} from "../types/domain";

export function DataReviewPage() {
  const [summary, setSummary] = useState<TeamReviewSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [squadGaps, setSquadGaps] = useState<SquadGapSummary | null>(null);
  const [squadGapsError, setSquadGapsError] = useState<string | null>(null);
  const [managerTrust, setManagerTrust] = useState<ManagerTacticalTrustSummary | null>(null);
  const [managerTrustError, setManagerTrustError] = useState<string | null>(null);
  const [ratingWorkbench, setRatingWorkbench] = useState<RatingReviewWorkbenchSummary | null>(null);
  const [ratingWorkbenchError, setRatingWorkbenchError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getTeamDataReview()
      .then(setSummary)
      .catch(() => setError("チームデータレビューの読み込みに失敗しました。"));
    api
      .getSquadGapReview()
      .then(setSquadGaps)
      .catch(() => setSquadGapsError("スカッド評価ギャップの読み込みに失敗しました。"));
    api
      .getManagerTacticalTrust()
      .then(setManagerTrust)
      .catch(() => setManagerTrustError("監督・戦術データレビューの読み込みに失敗しました。"));
    api
      .getRatingReviewWorkbench()
      .then(setRatingWorkbench)
      .catch(() => setRatingWorkbenchError("能力値レビュー作業台の読み込みに失敗しました。"));
  }, []);

  return (
    <div className="space-y-6">
      <section className="rounded-lg border border-slate-700 bg-slate-800/40 p-5">
        <h2 className="text-xl font-bold">データレビュー</h2>
        <p className="mt-1 text-sm text-slate-400">
          シミュレーション精度監査とロスター照合の結果から、チームごとのデータ見直し優先度を表示します。
        </p>
        <p className="mt-2 text-xs text-slate-500">
          このページは試合予測そのものを変更しません。次にCodexがどのチームのデータを確認すべきかを示すための診断です。
          フォーミュラの調整は別途の検証スペックがない限り行いません。
        </p>
      </section>

      {error && (
        <div className="rounded-lg border border-slate-700 bg-slate-800/40 p-4 text-center text-sm text-rose-400">{error}</div>
      )}

      {!summary && !error && <p className="text-sm text-slate-400">読み込み中...</p>}

      {summary && summary.teamCount === 0 && (
        <div className="rounded-lg border border-slate-700 bg-slate-800/40 p-4 text-center text-sm text-slate-400">
          {summary.note}
        </div>
      )}

      {summary && summary.teamCount > 0 && (
        <>
          <TeamDataReviewPanel summary={summary} />
          <p className="text-[11px] text-slate-500">{summary.note}</p>
        </>
      )}

      <section>
        <h3 className="mb-2 text-xs uppercase tracking-widest text-slate-500">スカッド評価ギャップ</h3>
        {squadGapsError && (
          <div className="rounded-lg border border-slate-700 bg-slate-800/40 p-4 text-center text-sm text-rose-400">
            {squadGapsError}
          </div>
        )}
        {!squadGaps && !squadGapsError && <p className="text-sm text-slate-400">読み込み中...</p>}
        {squadGaps && <SquadGapPanel summary={squadGaps} />}
      </section>

      <section>
        <h3 className="mb-2 text-xs uppercase tracking-widest text-slate-500">監督・戦術データの信頼性</h3>
        {managerTrustError && (
          <div className="rounded-lg border border-slate-700 bg-slate-800/40 p-4 text-center text-sm text-rose-400">
            {managerTrustError}
          </div>
        )}
        {!managerTrust && !managerTrustError && <p className="text-sm text-slate-400">読み込み中...</p>}
        {managerTrust && <ManagerTacticalTrustPanel summary={managerTrust} />}
      </section>

      <section>
        <h3 className="mb-2 text-xs uppercase tracking-widest text-slate-500">能力値レビュー作業台</h3>
        {ratingWorkbenchError && (
          <div className="rounded-lg border border-slate-700 bg-slate-800/40 p-4 text-center text-sm text-rose-400">
            {ratingWorkbenchError}
          </div>
        )}
        {!ratingWorkbench && !ratingWorkbenchError && <p className="text-sm text-slate-400">読み込み中...</p>}
        {ratingWorkbench && <RatingReviewWorkbenchPanel summary={ratingWorkbench} />}
      </section>
    </div>
  );
}
