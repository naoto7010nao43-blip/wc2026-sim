import type {
  ExternalDataVerificationSummary,
  ManagerTacticalTrustSummary,
  ModelCalibrationSummary,
  RatingDecisionAuditSummary,
  ReleaseReadinessSummary,
  SimulationStabilitySummary,
  SourceProvenanceAuditSummary,
  SubstitutionModelGapSummary,
  TeamReviewSummary,
} from "../types/domain";

interface Props {
  teamReview: TeamReviewSummary | null;
  managerTrust: ManagerTacticalTrustSummary | null;
  ratingDecisionAudit: RatingDecisionAuditSummary | null;
  sourceProvenanceAudit: SourceProvenanceAuditSummary | null;
  modelCalibration: ModelCalibrationSummary | null;
  releaseReadiness: ReleaseReadinessSummary | null;
  externalDataVerification: ExternalDataVerificationSummary | null;
  simulationStability: SimulationStabilitySummary | null;
  substitutionModelGap: SubstitutionModelGapSummary | null;
}

function bandLabel(band: string | null | undefined): string {
  if (band === "stable") return "安定";
  if (band === "usable") return "表示用に利用可";
  if (band === "volatile") return "揺れが大きい";
  return "未読込";
}

function modelStatusLabel(status: string | null | undefined): string {
  if (status === "pass") return "検証上は合格";
  if (status === "review") return "レビュー要";
  return "未読込";
}

function Metric({ label, value, tone = "slate" }: { label: string; value: string | number; tone?: "slate" | "good" | "warn" }) {
  const toneClass =
    tone === "good" ? "text-emerald-300" : tone === "warn" ? "text-amber-300" : "text-slate-100";
  return (
    <div className="rounded bg-slate-900/50 px-2 py-2">
      <p className="text-[11px] text-slate-500">{label}</p>
      <p className={`mt-1 text-sm font-semibold ${toneClass}`}>{value}</p>
    </div>
  );
}

export function DataReviewOverviewPanel({
  teamReview,
  managerTrust,
  ratingDecisionAudit,
  sourceProvenanceAudit,
  modelCalibration,
  releaseReadiness,
  externalDataVerification,
  simulationStability,
  substitutionModelGap,
}: Props) {
  const highPriorityTeams = teamReview?.teams.filter((team) => team.priority_band === "high").length ?? 0;
  const managerHighRisk = managerTrust?.bandCounts.high ?? 0;
  const laterProposalCandidates = ratingDecisionAudit?.bucketCounts.candidate_for_later_proposal ?? 0;
  const sourceReviewCandidates = sourceProvenanceAudit?.sourceReviewCandidateCount ?? 0;
  const sourceRiskPlayers = sourceProvenanceAudit?.seedSourceSummary.players_with_source_risk ?? 0;
  const stabilityBand = simulationStability?.summary?.stabilityBand;
  const maxStabilityDelta = simulationStability?.summary?.maxAbsChampionPctDelta;
  const externalCoveredTeams = externalDataVerification?.coveredTeamCount ?? 0;
  const externalTotalTeams = externalDataVerification?.totalTeamCount ?? 48;
  const externalWarnings = externalDataVerification?.decisionQueue?.warningHoldCount ?? externalDataVerification?.warningCount ?? 0;
  const externalReadyForReview =
    externalDataVerification?.decisionQueue?.currentFieldReviewCount ??
    externalDataVerification?.useTierCounts.ready_for_codex_review ??
    0;
  const substitutionNeedsSpec = substitutionModelGap?.summary?.currentModelHasManagerSpecificSubstitutions === false;
  const releaseBlocked = releaseReadiness?.readyForManualPush === false;

  const actions = [
    highPriorityTeams > 0 ? `高優先度チーム ${highPriorityTeams}件をデータ更新候補として確認` : null,
    laterProposalCandidates > 0 ? `能力値の将来提案候補 ${laterProposalCandidates}件を出典と照合` : null,
    externalReadyForReview > 0 ? `外部調査のCodexレビュー候補 ${externalReadyForReview}件をseed反映前に精査` : null,
    externalWarnings > 0 ? `外部調査の警告 ${externalWarnings}件は反映候補から一段止める` : null,
    sourceReviewCandidates > 0 ? `出典確認が先の候補 ${sourceReviewCandidates}件を保留` : null,
    substitutionNeedsSpec ? "選手交代傾向は現エンジンに反映先がないため、将来仕様候補として扱う" : null,
    releaseBlocked ? `本番反映は${releaseReadiness?.blockers.length ?? 0}件の理由で保留` : null,
  ].filter((item): item is string => Boolean(item));

  return (
    <section className="rounded-lg border border-slate-700 bg-slate-800/40 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-bold text-slate-200">レビュー総合サマリー</h3>
          <p className="mt-1 text-xs text-slate-400">
            精度改善に直結する監査だけを束ねた入口です。数値は診断レポート由来で、seedデータや予測式はここでは変更しません。
          </p>
        </div>
        <span className="rounded bg-sky-500/15 px-2 py-1 text-[10px] font-semibold text-sky-300">Codex判断用</span>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-2 md:grid-cols-4">
        <Metric label="モデル検証" value={modelStatusLabel(modelCalibration?.status)} tone={modelCalibration?.status === "pass" ? "good" : "warn"} />
        <Metric
          label="確率安定性"
          value={maxStabilityDelta === undefined ? bandLabel(stabilityBand) : `${bandLabel(stabilityBand)} / 最大${maxStabilityDelta.toFixed(1)}pt`}
          tone={stabilityBand === "volatile" ? "warn" : "good"}
        />
        <Metric label="高優先度チーム" value={highPriorityTeams} tone={highPriorityTeams > 0 ? "warn" : "good"} />
        <Metric label="出典リスク選手" value={sourceRiskPlayers} tone={sourceRiskPlayers > 0 ? "warn" : "good"} />
        <Metric
          label="外部調査進捗"
          value={`${externalCoveredTeams}/${externalTotalTeams}`}
          tone={externalCoveredTeams >= externalTotalTeams ? "good" : "warn"}
        />
        <Metric label="監督・戦術High" value={managerHighRisk} tone={managerHighRisk > 0 ? "warn" : "good"} />
        <Metric label="能力値提案候補" value={laterProposalCandidates} tone={laterProposalCandidates > 0 ? "warn" : "slate"} />
        <Metric label="出典確認候補" value={sourceReviewCandidates} tone={sourceReviewCandidates > 0 ? "warn" : "good"} />
        <Metric label="交代モデル" value={substitutionNeedsSpec ? "将来仕様候補" : "現行対応"} tone={substitutionNeedsSpec ? "warn" : "good"} />
        <Metric label="本番反映" value={releaseReadiness?.readyForManualPush ? "可能" : "保留"} tone={releaseReadiness?.readyForManualPush ? "good" : "warn"} />
      </div>

      {actions.length > 0 && (
        <div className="mt-3 rounded border border-slate-700/70 bg-slate-900/40 p-3">
          <p className="text-[11px] font-semibold text-slate-300">次に見るべき点</p>
          <div className="mt-2 grid grid-cols-1 gap-1.5 text-[11px] text-slate-400 md:grid-cols-2">
            {actions.map((action) => (
              <p key={action}>・{action}</p>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
