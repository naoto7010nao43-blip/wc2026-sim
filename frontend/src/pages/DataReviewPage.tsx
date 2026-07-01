import { useEffect, useState } from "react";
import { api } from "../api/client";
import { DataFreshnessPanel } from "../components/DataFreshnessPanel";
import { DataReviewOverviewPanel } from "../components/DataReviewOverviewPanel";
import { ExternalDataVerificationPanel } from "../components/ExternalDataVerificationPanel";
import { ManagerTacticalTrustPanel } from "../components/ManagerTacticalTrustPanel";
import { ModelCalibrationPanel } from "../components/ModelCalibrationPanel";
import { RatingDecisionAuditPanel } from "../components/RatingDecisionAuditPanel";
import { RatingReviewWorkbenchPanel } from "../components/RatingReviewWorkbenchPanel";
import { ReleaseReadinessPanel } from "../components/ReleaseReadinessPanel";
import { SimulationStabilityPanel } from "../components/SimulationStabilityPanel";
import { SourceProvenanceAuditPanel } from "../components/SourceProvenanceAuditPanel";
import { SquadGapPanel } from "../components/SquadGapPanel";
import { SubstitutionModelGapPanel } from "../components/SubstitutionModelGapPanel";
import { SubstitutionProfileCandidatePanel } from "../components/SubstitutionProfileCandidatePanel";
import { TeamDataReviewPanel } from "../components/TeamDataReviewPanel";
import type {
  DataQualitySummary,
  ExternalDataVerificationSummary,
  ManagerTacticalTrustSummary,
  ModelCalibrationSummary,
  RatingDecisionAuditSummary,
  RatingReviewWorkbenchSummary,
  ReleaseReadinessSummary,
  SimulationStabilitySummary,
  SourceProvenanceAuditSummary,
  SquadGapSummary,
  SubstitutionModelGapSummary,
  SubstitutionProfileCandidateQueueSummary,
  TeamReviewSummary,
} from "../types/domain";

const REVIEW_SECTIONS = [
  { id: "data-freshness", label: "鮮度" },
  { id: "model-calibration", label: "モデル" },
  { id: "simulation-stability", label: "確率安定性" },
  { id: "external-data", label: "外部調査" },
  { id: "substitution-gap", label: "選手交代" },
  { id: "substitution-candidates", label: "交代候補" },
  { id: "team-review", label: "チーム優先度" },
  { id: "squad-gaps", label: "スカッド" },
  { id: "manager-trust", label: "監督・戦術" },
  { id: "rating-workbench", label: "能力値候補" },
  { id: "rating-decision", label: "判断監査" },
  { id: "source-provenance", label: "出典" },
];

export function DataReviewPage() {
  const [summary, setSummary] = useState<TeamReviewSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dataQuality, setDataQuality] = useState<DataQualitySummary | null>(null);
  const [dataQualityError, setDataQualityError] = useState<string | null>(null);
  const [squadGaps, setSquadGaps] = useState<SquadGapSummary | null>(null);
  const [squadGapsError, setSquadGapsError] = useState<string | null>(null);
  const [managerTrust, setManagerTrust] = useState<ManagerTacticalTrustSummary | null>(null);
  const [managerTrustError, setManagerTrustError] = useState<string | null>(null);
  const [ratingWorkbench, setRatingWorkbench] = useState<RatingReviewWorkbenchSummary | null>(null);
  const [ratingWorkbenchError, setRatingWorkbenchError] = useState<string | null>(null);
  const [ratingDecisionAudit, setRatingDecisionAudit] = useState<RatingDecisionAuditSummary | null>(null);
  const [ratingDecisionAuditError, setRatingDecisionAuditError] = useState<string | null>(null);
  const [sourceProvenanceAudit, setSourceProvenanceAudit] = useState<SourceProvenanceAuditSummary | null>(null);
  const [sourceProvenanceAuditError, setSourceProvenanceAuditError] = useState<string | null>(null);
  const [modelCalibration, setModelCalibration] = useState<ModelCalibrationSummary | null>(null);
  const [modelCalibrationError, setModelCalibrationError] = useState<string | null>(null);
  const [releaseReadiness, setReleaseReadiness] = useState<ReleaseReadinessSummary | null>(null);
  const [releaseReadinessError, setReleaseReadinessError] = useState<string | null>(null);
  const [externalDataVerification, setExternalDataVerification] = useState<ExternalDataVerificationSummary | null>(null);
  const [externalDataVerificationError, setExternalDataVerificationError] = useState<string | null>(null);
  const [simulationStability, setSimulationStability] = useState<SimulationStabilitySummary | null>(null);
  const [simulationStabilityError, setSimulationStabilityError] = useState<string | null>(null);
  const [substitutionModelGap, setSubstitutionModelGap] = useState<SubstitutionModelGapSummary | null>(null);
  const [substitutionModelGapError, setSubstitutionModelGapError] = useState<string | null>(null);
  const [substitutionProfileCandidates, setSubstitutionProfileCandidates] =
    useState<SubstitutionProfileCandidateQueueSummary | null>(null);
  const [substitutionProfileCandidatesError, setSubstitutionProfileCandidatesError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getDataQualitySummary()
      .then(setDataQuality)
      .catch(() => setDataQualityError("データ鮮度・品質情報の読み込みに失敗しました。"));
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
    api
      .getRatingDecisionAudit()
      .then(setRatingDecisionAudit)
      .catch(() => setRatingDecisionAuditError("能力値レビュー判断監査の読み込みに失敗しました。"));
    api
      .getSourceProvenanceAudit()
      .then(setSourceProvenanceAudit)
      .catch(() => setSourceProvenanceAuditError("出典監査の読み込みに失敗しました。"));
    api
      .getModelCalibrationSummary()
      .then(setModelCalibration)
      .catch(() => setModelCalibrationError("モデルキャリブレーションの読み込みに失敗しました。"));
    api
      .getReleaseReadinessSummary()
      .then(setReleaseReadiness)
      .catch(() => setReleaseReadinessError("本番反映readinessの読み込みに失敗しました。"));
    api
      .getExternalDataVerificationSummary()
      .then(setExternalDataVerification)
      .catch(() => setExternalDataVerificationError("外部データ検証の読み込みに失敗しました。"));
    api
      .getSimulationStabilitySummary()
      .then(setSimulationStability)
      .catch(() => setSimulationStabilityError("モンテカルロ安定性監査の読み込みに失敗しました。"));
    api
      .getSubstitutionModelGapSummary()
      .then(setSubstitutionModelGap)
      .catch(() => setSubstitutionModelGapError("選手交代モデルのギャップ監査の読み込みに失敗しました。"));
    api
      .getSubstitutionProfileCandidates()
      .then(setSubstitutionProfileCandidates)
      .catch(() => setSubstitutionProfileCandidatesError("交代プロファイル候補の読み込みに失敗しました。"));
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

      <DataReviewOverviewPanel
        teamReview={summary}
        managerTrust={managerTrust}
        ratingDecisionAudit={ratingDecisionAudit}
        sourceProvenanceAudit={sourceProvenanceAudit}
        modelCalibration={modelCalibration}
        releaseReadiness={releaseReadiness}
        dataQuality={dataQuality}
        externalDataVerification={externalDataVerification}
        simulationStability={simulationStability}
        substitutionModelGap={substitutionModelGap}
        substitutionProfileCandidates={substitutionProfileCandidates}
      />

      {releaseReadinessError && (
        <div className="rounded-lg border border-slate-700 bg-slate-800/40 p-4 text-center text-sm text-rose-400">
          {releaseReadinessError}
        </div>
      )}
      {!releaseReadiness && !releaseReadinessError && <p className="text-sm text-slate-400">読み込み中...</p>}
      {releaseReadiness && <ReleaseReadinessPanel summary={releaseReadiness} />}

      <nav className="flex flex-wrap gap-2" aria-label="データレビュー索引">
        {REVIEW_SECTIONS.map((section) => (
          <a
            key={section.id}
            href={`#${section.id}`}
            className="rounded border border-slate-700 bg-slate-800/50 px-2 py-1 text-xs text-slate-300 transition hover:border-sky-500 hover:text-sky-200"
          >
            {section.label}
          </a>
        ))}
      </nav>

      <section id="data-freshness" className="scroll-mt-4">
        {dataQualityError && (
          <div className="rounded-lg border border-slate-700 bg-slate-800/40 p-4 text-center text-sm text-rose-400">
            {dataQualityError}
          </div>
        )}
        {!dataQuality && !dataQualityError && <p className="text-sm text-slate-400">読み込み中...</p>}
        {dataQuality && <DataFreshnessPanel summary={dataQuality} />}
      </section>

      <section id="model-calibration" className="scroll-mt-4">
        {modelCalibrationError && (
          <div className="rounded-lg border border-slate-700 bg-slate-800/40 p-4 text-center text-sm text-rose-400">
            {modelCalibrationError}
          </div>
        )}
        {!modelCalibration && !modelCalibrationError && <p className="text-sm text-slate-400">読み込み中...</p>}
        {modelCalibration && <ModelCalibrationPanel summary={modelCalibration} />}
      </section>

      <section id="simulation-stability" className="scroll-mt-4">
        {simulationStabilityError && (
          <div className="rounded-lg border border-slate-700 bg-slate-800/40 p-4 text-center text-sm text-rose-400">
            {simulationStabilityError}
          </div>
        )}
        {!simulationStability && !simulationStabilityError && <p className="text-sm text-slate-400">読み込み中...</p>}
        {simulationStability && <SimulationStabilityPanel summary={simulationStability} />}
      </section>

      <section id="external-data" className="scroll-mt-4">
        {externalDataVerificationError && (
          <div className="rounded-lg border border-slate-700 bg-slate-800/40 p-4 text-center text-sm text-rose-400">
            {externalDataVerificationError}
          </div>
        )}
        {!externalDataVerification && !externalDataVerificationError && <p className="text-sm text-slate-400">読み込み中...</p>}
        {externalDataVerification && <ExternalDataVerificationPanel summary={externalDataVerification} />}
      </section>

      <section id="substitution-gap" className="scroll-mt-4">
        {substitutionModelGapError && (
          <div className="rounded-lg border border-slate-700 bg-slate-800/40 p-4 text-center text-sm text-rose-400">
            {substitutionModelGapError}
          </div>
        )}
        {!substitutionModelGap && !substitutionModelGapError && <p className="text-sm text-slate-400">読み込み中...</p>}
        {substitutionModelGap && <SubstitutionModelGapPanel summary={substitutionModelGap} />}
      </section>

      <section id="substitution-candidates" className="scroll-mt-4">
        {substitutionProfileCandidatesError && (
          <div className="rounded-lg border border-slate-700 bg-slate-800/40 p-4 text-center text-sm text-rose-400">
            {substitutionProfileCandidatesError}
          </div>
        )}
        {!substitutionProfileCandidates && !substitutionProfileCandidatesError && (
          <p className="text-sm text-slate-400">読み込み中...</p>
        )}
        {substitutionProfileCandidates && <SubstitutionProfileCandidatePanel summary={substitutionProfileCandidates} />}
      </section>

      {error && (
        <div className="rounded-lg border border-slate-700 bg-slate-800/40 p-4 text-center text-sm text-rose-400">{error}</div>
      )}

      {!summary && !error && <p className="text-sm text-slate-400">読み込み中...</p>}

      <section id="team-review" className="scroll-mt-4">
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
      </section>

      <section id="squad-gaps" className="scroll-mt-4">
        <h3 className="mb-2 text-xs uppercase tracking-widest text-slate-500">スカッド評価ギャップ</h3>
        {squadGapsError && (
          <div className="rounded-lg border border-slate-700 bg-slate-800/40 p-4 text-center text-sm text-rose-400">
            {squadGapsError}
          </div>
        )}
        {!squadGaps && !squadGapsError && <p className="text-sm text-slate-400">読み込み中...</p>}
        {squadGaps && <SquadGapPanel summary={squadGaps} />}
      </section>

      <section id="manager-trust" className="scroll-mt-4">
        <h3 className="mb-2 text-xs uppercase tracking-widest text-slate-500">監督・戦術データの信頼性</h3>
        {managerTrustError && (
          <div className="rounded-lg border border-slate-700 bg-slate-800/40 p-4 text-center text-sm text-rose-400">
            {managerTrustError}
          </div>
        )}
        {!managerTrust && !managerTrustError && <p className="text-sm text-slate-400">読み込み中...</p>}
        {managerTrust && <ManagerTacticalTrustPanel summary={managerTrust} />}
      </section>

      <section id="rating-workbench" className="scroll-mt-4">
        <h3 className="mb-2 text-xs uppercase tracking-widest text-slate-500">能力値レビュー作業台</h3>
        {ratingWorkbenchError && (
          <div className="rounded-lg border border-slate-700 bg-slate-800/40 p-4 text-center text-sm text-rose-400">
            {ratingWorkbenchError}
          </div>
        )}
        {!ratingWorkbench && !ratingWorkbenchError && <p className="text-sm text-slate-400">読み込み中...</p>}
        {ratingWorkbench && <RatingReviewWorkbenchPanel summary={ratingWorkbench} />}
      </section>

      <section id="rating-decision" className="scroll-mt-4">
        <h3 className="mb-2 text-xs uppercase tracking-widest text-slate-500">能力値レビュー判断監査</h3>
        {ratingDecisionAuditError && (
          <div className="rounded-lg border border-slate-700 bg-slate-800/40 p-4 text-center text-sm text-rose-400">
            {ratingDecisionAuditError}
          </div>
        )}
        {!ratingDecisionAudit && !ratingDecisionAuditError && <p className="text-sm text-slate-400">読み込み中...</p>}
        {ratingDecisionAudit && <RatingDecisionAuditPanel summary={ratingDecisionAudit} />}
      </section>

      <section id="source-provenance" className="scroll-mt-4">
        <h3 className="mb-2 text-xs uppercase tracking-widest text-slate-500">出典監査</h3>
        {sourceProvenanceAuditError && (
          <div className="rounded-lg border border-slate-700 bg-slate-800/40 p-4 text-center text-sm text-rose-400">
            {sourceProvenanceAuditError}
          </div>
        )}
        {!sourceProvenanceAudit && !sourceProvenanceAuditError && <p className="text-sm text-slate-400">読み込み中...</p>}
        {sourceProvenanceAudit && <SourceProvenanceAuditPanel summary={sourceProvenanceAudit} />}
      </section>
    </div>
  );
}
