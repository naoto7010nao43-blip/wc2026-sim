import type { SubstitutionProfileCandidateQueueSummary } from "../types/domain";

interface Props {
  summary: SubstitutionProfileCandidateQueueSummary;
}

const BAND_LABELS: Record<string, string> = {
  profile_review_ready: "レビュー準備あり",
  needs_more_match_evidence: "追加根拠待ち",
  hold_for_source_review: "出典確認待ち",
  low_confidence_context: "低信頼の文脈",
};

const SIGNAL_LABELS: Record<string, string> = {
  bench_trust: "控え信頼度",
  first_sub_minute_bias: "初回交代タイミング",
  late_penalty_prep_bias: "PK/延長準備",
  leading_defensive_bias: "リード時守備固め",
  like_for_like_preference: "同ポジション志向",
  manual_substitution_profile_review: "手動レビュー",
  trailing_aggression: "ビハインド時攻撃性",
};

function bandTone(band: string): string {
  if (band === "profile_review_ready") return "border-emerald-500/40 bg-emerald-500/10 text-emerald-300";
  if (band === "needs_more_match_evidence") return "border-sky-500/40 bg-sky-500/10 text-sky-300";
  return "border-amber-500/40 bg-amber-500/10 text-amber-300";
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded bg-slate-900/50 px-2 py-2 text-center">
      <p className="text-[11px] text-slate-500">{label}</p>
      <p className="mt-1 text-sm font-semibold text-slate-100">{value}</p>
    </div>
  );
}

export function SubstitutionProfileCandidatePanel({ summary }: Props) {
  if (summary.teamCount === 0) {
    return (
      <div className="rounded-lg border border-slate-700 bg-slate-800/40 p-4 text-center text-sm text-slate-400">
        {summary.note}
      </div>
    );
  }

  const topTeams = summary.teams.slice(0, 12);
  const topSignals = Object.entries(summary.signalCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6);

  return (
    <section className="rounded-lg border border-slate-700 bg-slate-800/40 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-bold text-slate-200">交代プロファイル候補キュー</h3>
          <p className="mt-1 max-w-3xl text-xs text-slate-400">{summary.note}</p>
        </div>
        <span className="rounded bg-sky-500/15 px-2 py-1 text-[10px] font-semibold text-sky-300">
          読み取り専用
        </span>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-2 md:grid-cols-4">
        <Metric label="交代候補" value={summary.candidateCount} />
        <Metric label="対象チーム" value={summary.teamCount} />
        <Metric label="レビュー準備" value={summary.readyTeamCount} />
        <Metric label="保留/低信頼" value={summary.holdTeamCount} />
      </div>

      <div className="mt-3 flex flex-wrap gap-1.5">
        {topSignals.map(([signal, count]) => (
          <span key={signal} className="rounded bg-slate-900/60 px-2 py-1 text-[10px] text-slate-300">
            {SIGNAL_LABELS[signal] ?? signal}: {count}
          </span>
        ))}
      </div>

      <div className="mt-4 grid grid-cols-1 gap-3 lg:grid-cols-2">
        {topTeams.map((team) => (
          <div key={team.teamId} className="rounded border border-slate-700/70 bg-slate-900/40 p-3">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <p className="text-xs font-semibold text-slate-100">
                  {team.teamId} <span className="text-slate-400">{team.teamName}</span>
                </p>
                <p className="mt-1 text-[11px] text-slate-500">
                  score {team.readinessScore.toFixed(1)} / source {team.strongestSourceTier ?? "-"} / confidence{" "}
                  {team.confidenceBand ?? "-"}
                </p>
              </div>
              <span className={`rounded border px-1.5 py-0.5 text-[10px] font-semibold ${bandTone(team.readinessBand)}`}>
                {BAND_LABELS[team.readinessBand] ?? team.readinessBand}
              </span>
            </div>

            <div className="mt-2 flex flex-wrap gap-1">
              {team.suggestedProfileSignals.map((signal) => (
                <span key={signal} className="rounded bg-sky-500/10 px-1.5 py-0.5 text-[10px] text-sky-300">
                  {SIGNAL_LABELS[signal] ?? signal}
                </span>
              ))}
            </div>

            <p className="mt-2 max-h-14 overflow-hidden text-[11px] text-slate-400">{team.evidenceSummaries[0]}</p>
            <p className="mt-2 text-[11px] text-amber-200/90">{team.recommendedHandlingJa}</p>
          </div>
        ))}
      </div>

      <div className="mt-3 space-y-1 text-[11px] text-slate-400">
        {summary.recommendationsJa.map((line) => (
          <p key={line}>・{line}</p>
        ))}
      </div>
    </section>
  );
}
