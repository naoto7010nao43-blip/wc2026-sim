import type { SubstitutionModelGapSummary } from "../types/domain";

interface Props {
  summary: SubstitutionModelGapSummary;
}

const RULE_LABELS: Record<string, string> = {
  most_fatigued_matching_position_best_overall_bench: "疲労した選手を近いポジションの控えへ交代",
};

export function SubstitutionModelGapPanel({ summary }: Props) {
  if (!summary.summary || !summary.engineCapabilities) {
    return (
      <div className="rounded-lg border border-slate-700 bg-slate-800/40 p-4 text-center text-sm text-slate-400">
        {summary.note}
      </div>
    );
  }

  const capabilities = summary.engineCapabilities;

  return (
    <section className="rounded-lg border border-slate-700 bg-slate-800/40 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-bold text-slate-200">選手交代モデルのギャップ</h3>
          <p className="mt-1 max-w-3xl text-xs text-slate-400">{summary.note}</p>
        </div>
        <span className="rounded bg-amber-500/15 px-2 py-1 text-[10px] font-semibold text-amber-300">
          将来仕様候補
        </span>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-2 text-[11px] md:grid-cols-4">
        <Metric label="最大交代数" value={`${capabilities.maxSubs}人`} />
        <Metric label="交代時間帯" value={`${capabilities.subWindow.startMinute}-${capabilities.subWindow.endMinute}分`} />
        <Metric label="毎分の検討確率" value={`${Math.round(capabilities.subChancePerMinute * 100)}%`} />
        <Metric
          label="監督別プロファイル機構"
          value={capabilities.hasManagerSpecificSubstitutionParameters ? "実装済み" : "なし"}
        />
      </div>
      {capabilities.hasManagerSpecificSubstitutionParameters && !capabilities.anyTeamUsesNonNeutralProfile && (
        <p className="mt-2 text-[11px] text-amber-200/90">
          交代プロファイルの仕組み自体はエンジンに実装済みですが、現在は全チームが中立値のままで、
          チーム間の実質的な交代傾向の差はまだありません。
        </p>
      )}

      <div className="mt-3 rounded border border-slate-700/70 bg-slate-900/40 p-3">
        <p className="text-[11px] font-semibold text-slate-300">現在の交代ルール</p>
        <p className="mt-1 text-xs text-slate-400">{RULE_LABELS[capabilities.selectionRule] ?? capabilities.selectionRule}</p>
      </div>

      <div className="mt-3 grid grid-cols-1 gap-3 lg:grid-cols-2">
        {summary.gaps.map((gap) => (
          <div key={gap.gapId} className="rounded border border-slate-700/70 bg-slate-900/40 p-3">
            <div className="flex items-center justify-between gap-2">
              <p className="text-xs font-semibold text-slate-200">{gap.label}</p>
              <span className="rounded bg-slate-700/70 px-1.5 py-0.5 text-[10px] text-slate-300">
                {capabilities.anyTeamUsesNonNeutralProfile ? "一部反映" : "中立値のまま"}
              </span>
            </div>
            <p className="mt-2 text-[11px] text-slate-400">{gap.currentBehavior}</p>
            <p className="mt-2 text-[11px] text-amber-200/90">{gap.precisionRiskJa}</p>
            <div className="mt-2 flex flex-wrap gap-1">
              {gap.futureFieldCandidates.map((field) => (
                <span key={field} className="rounded bg-sky-500/10 px-1.5 py-0.5 text-[10px] text-sky-300">
                  {field}
                </span>
              ))}
            </div>
            <p className="mt-2 text-[11px] text-slate-500">{gap.evidenceNeededJa}</p>
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

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded bg-slate-900/50 px-2 py-2 text-center">
      <p className="text-slate-500">{label}</p>
      <p className="mt-1 font-semibold text-slate-100">{value}</p>
    </div>
  );
}
