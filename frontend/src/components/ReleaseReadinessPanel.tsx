import type { ReleaseReadinessSummary } from "../types/domain";

interface Props {
  summary: ReleaseReadinessSummary;
}

function blockerLabel(blocker: string): string {
  if (blocker.includes("CURRENT_TASK.md")) return "Claude CodeのActiveタスクが残っています";
  if (blocker.includes("git status")) return "未コミット差分があります";
  if (blocker.includes("required report")) return "必須診断レポートが不足しています";
  if (blocker.includes("benchmark")) return "モデルベンチマークが未合格です";
  return blocker;
}

export function ReleaseReadinessPanel({ summary }: Props) {
  const presentReports = summary.requiredReports.filter((report) => report.present).length;
  const missingReports = summary.requiredReports.length - presentReports;

  return (
    <section className="rounded-lg border border-slate-700 bg-slate-800/40 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-bold text-slate-200">本番反映 readiness</h3>
          <p className="mt-1 text-xs text-slate-400">{summary.note}</p>
        </div>
        <span
          className={`rounded px-2 py-1 text-[10px] font-semibold ${
            summary.readyForManualPush ? "bg-emerald-500/15 text-emerald-300" : "bg-amber-500/15 text-amber-300"
          }`}
        >
          {summary.readyForManualPush ? "手動push可能" : "保留"}
        </span>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-2 text-[11px] md:grid-cols-4">
        <Metric label="必須レポート" value={`${presentReports}/${summary.requiredReports.length}`} tone={missingReports === 0 ? "good" : "warn"} />
        <Metric label="不足レポート" value={missingReports} tone={missingReports === 0 ? "good" : "warn"} />
        <Metric label="作業ツリー" value={summary.gitStatusShort.length === 0 ? "clean" : `${summary.gitStatusShort.length}件`} tone={summary.gitStatusShort.length === 0 ? "good" : "warn"} />
        <Metric label="Benchmark" value={summary.rank75Benchmark?.status ?? "未生成"} tone={summary.rank75Benchmark?.status === "pass" ? "good" : "warn"} />
      </div>

      {summary.modelVersions && (
        <div className="mt-3 rounded border border-slate-700/70 bg-slate-900/40 p-3 text-[11px] text-slate-400">
          <p>
            <span className="text-slate-500">比較:</span> {summary.modelVersions.baselineModelVersion ?? "-"} →{" "}
            {summary.modelVersions.currentModelVersion ?? "-"}
          </p>
          {summary.rank75Benchmark?.benchmarkMethod && (
            <p className="mt-1">
              <span className="text-slate-500">測定:</span> {summary.rank75Benchmark.benchmarkMethod}
            </p>
          )}
        </div>
      )}

      {summary.blockers.length > 0 && (
        <div className="mt-3 rounded border border-amber-500/30 bg-amber-500/10 p-3">
          <p className="text-[11px] font-semibold text-amber-200">残っている保留理由</p>
          <div className="mt-2 space-y-1 text-[11px] text-amber-100/85">
            {summary.blockers.map((blocker) => (
              <p key={blocker}>・{blockerLabel(blocker)}</p>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}

function Metric({ label, value, tone }: { label: string; value: string | number; tone: "good" | "warn" }) {
  return (
    <div className="rounded bg-slate-900/50 px-2 py-2 text-center">
      <p className="text-slate-500">{label}</p>
      <p className={`mt-1 font-semibold ${tone === "good" ? "text-emerald-300" : "text-amber-300"}`}>{value}</p>
    </div>
  );
}
