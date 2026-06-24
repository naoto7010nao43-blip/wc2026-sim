import type { ExternalDataVerificationSummary } from "../types/domain";
import { TeamBadge } from "./TeamBadge";

interface Props {
  summary: ExternalDataVerificationSummary;
}

const CATEGORY_LABELS: Record<string, string> = {
  formationCandidates: "フォーメーション",
  keyPlayerStatusCandidates: "主力選手",
  managerStatus: "監督情報",
  nationalStrengthContext: "国としての文脈",
  substitutionTendencyCandidates: "選手交代",
  tacticalProfileCandidates: "戦術傾向",
};

const USE_TIER_LABELS: Record<string, string> = {
  ready_for_codex_review: "Codexレビュー候補",
  provisional_context: "暫定文脈",
  future_engine_candidate: "将来エンジン候補",
  review_question: "確認質問として保留",
};

const SIGNAL_LABELS: Record<string, string> = {
  strong: "十分",
  moderate: "中程度",
  sparse: "薄い",
  weak: "弱い",
};

function warningLabel(warning: string): string {
  const teamMatch = warning.match(/teams\[([A-Z]{3})\]/);
  const team = teamMatch ? `${teamMatch[1]}: ` : "";
  if (warning.includes("Tier B but high confidence")) {
    return `${team}Tier B情報が高信頼扱いです。seedや能力値へ使う前に追加確認してください。`;
  }
  if (warning.includes("uses Tier C evidence")) {
    return `${team}Tier C情報です。反映候補ではなくレビュー質問として保留してください。`;
  }
  return `${team}${warning}`;
}

function Metric({
  label,
  value,
  tone = "slate",
}: {
  label: string;
  value: string | number;
  tone?: "slate" | "good" | "warn";
}) {
  const toneClass =
    tone === "good" ? "text-emerald-300" : tone === "warn" ? "text-amber-300" : "text-slate-100";
  return (
    <div className="rounded bg-slate-900/50 px-2 py-2 text-center">
      <p className="text-[11px] text-slate-500">{label}</p>
      <p className={`mt-1 text-sm font-semibold ${toneClass}`}>{value}</p>
    </div>
  );
}

function CountList({ title, counts, labels }: { title: string; counts: Record<string, number>; labels: Record<string, string> }) {
  const entries = Object.entries(counts).filter(([, count]) => count > 0);
  if (entries.length === 0) return null;
  return (
    <div className="rounded bg-slate-900/50 p-3">
      <p className="text-xs font-semibold text-slate-300">{title}</p>
      <div className="mt-2 space-y-1">
        {entries.map(([key, count]) => (
          <div key={key} className="flex items-center justify-between gap-2 text-[11px]">
            <span className="text-slate-400">{labels[key] ?? key}</span>
            <span className="font-semibold text-slate-200">{count}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function ExternalDataVerificationPanel({ summary }: Props) {
  const coverage =
    summary.totalTeamCount > 0 ? `${summary.coveredTeamCount}/${summary.totalTeamCount}` : `${summary.coveredTeamCount}`;
  const readyForCodex = summary.useTierCounts.ready_for_codex_review ?? 0;
  const futureEngine = summary.useTierCounts.future_engine_candidate ?? 0;
  const highImpact = summary.impactCounts.high ?? 0;
  const remainingPreview = summary.scope?.remainingUnresearchedTeams.slice(0, 18) ?? [];
  const remainingRest = Math.max(0, summary.remainingTeamCount - remainingPreview.length);

  return (
    <section className="rounded-lg border border-slate-700 bg-slate-800/40 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-bold text-slate-200">外部データ検証</h3>
          <p className="mt-1 max-w-3xl text-xs text-slate-400">{summary.note}</p>
        </div>
        <span
          className={`rounded px-2 py-1 text-[10px] font-semibold ${
            summary.valid ? "bg-emerald-500/15 text-emerald-300" : "bg-amber-500/15 text-amber-300"
          }`}
        >
          {summary.valid ? "構造検証OK" : "要確認"}
        </span>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-2 text-[11px] md:grid-cols-4">
        <Metric label="調査済み国" value={coverage} tone={summary.remainingTeamCount === 0 ? "good" : "warn"} />
        <Metric label="未調査国" value={summary.remainingTeamCount} tone={summary.remainingTeamCount === 0 ? "good" : "warn"} />
        <Metric label="候補総数" value={summary.candidateCount} />
        <Metric label="Codexレビュー候補" value={readyForCodex} tone={readyForCodex > 0 ? "warn" : "good"} />
        <Metric label="高影響候補" value={highImpact} tone={highImpact > 0 ? "warn" : "slate"} />
        <Metric label="将来エンジン候補" value={futureEngine} tone={futureEngine > 0 ? "warn" : "slate"} />
        <Metric label="警告" value={summary.warningCount} tone={summary.warningCount > 0 ? "warn" : "good"} />
        <Metric label="エラー" value={summary.errorCount} tone={summary.errorCount > 0 ? "warn" : "good"} />
      </div>

      <div className="mt-3 grid grid-cols-1 gap-3 lg:grid-cols-3">
        <CountList title="カテゴリ別候補" counts={summary.categoryCounts} labels={CATEGORY_LABELS} />
        <CountList title="用途別の扱い" counts={summary.useTierCounts} labels={USE_TIER_LABELS} />
        <CountList title="チーム別シグナル密度" counts={summary.teamSignalBandCounts} labels={SIGNAL_LABELS} />
      </div>

      {summary.topTeamPriorities.length > 0 && (
        <div className="mt-3 rounded border border-slate-700/70 bg-slate-900/40 p-3">
          <p className="text-xs font-semibold text-slate-300">レビュー優先チーム</p>
          <div className="mt-2 grid grid-cols-1 gap-1.5 md:grid-cols-2">
            {summary.topTeamPriorities.slice(0, 8).map((team) => (
              <div key={team.teamId} className="flex items-center justify-between gap-2 rounded bg-slate-800/60 px-2 py-1.5 text-[11px]">
                <TeamBadge teamId={team.teamId} />
                <span className="text-slate-400">
                  高{team.highImpactCandidateCount} / 中{team.mediumImpactCandidateCount} / 将来{team.futureEngineCandidateCount}
                </span>
                <span className="font-semibold text-slate-200">{team.priorityScore.toFixed(0)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {summary.warnings.length > 0 && (
        <div className="mt-3 rounded border border-amber-500/30 bg-amber-500/10 p-3">
          <p className="text-[11px] font-semibold text-amber-200">反映前に止めるべき確認点</p>
          <div className="mt-2 space-y-1 text-[11px] text-amber-100/85">
            {summary.warnings.map((warning) => (
              <p key={warning}>・{warningLabel(warning)}</p>
            ))}
          </div>
        </div>
      )}

      {remainingPreview.length > 0 && (
        <div className="mt-3 rounded border border-slate-700/70 bg-slate-900/40 p-3">
          <p className="text-[11px] font-semibold text-slate-300">次にClaude Codeが継続すべき未調査国</p>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {remainingPreview.map((teamId) => (
              <TeamBadge key={teamId} teamId={teamId} />
            ))}
            {remainingRest > 0 && <span className="text-[11px] text-slate-500">ほか{remainingRest}か国</span>}
          </div>
        </div>
      )}
    </section>
  );
}
