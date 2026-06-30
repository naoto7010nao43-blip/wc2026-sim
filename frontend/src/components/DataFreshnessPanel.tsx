import type { DataQualitySummary } from "../types/domain";

interface Props {
  summary: DataQualitySummary;
}

const FRESHNESS_LABELS: Record<string, string> = {
  ok: "良好",
  warning: "一部注意",
  critical: "再確認推奨",
};

function formatDate(value: string | null): string {
  if (!value) return "不明";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "不明";
  return date.toLocaleDateString("ja-JP", { year: "numeric", month: "short", day: "numeric" });
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

export function DataFreshnessPanel({ summary }: Props) {
  const realResultTone = summary.real_group_match_count >= summary.real_group_match_expected ? "good" : "warn";
  const officialCoverageTone = summary.official_profile_coverage_pct >= 85 ? "good" : "warn";
  const highValueNotes = summary.notes.filter(
    (note) => note.includes("鮮度") || note.includes("公式スカッドfeed") || note.includes("seedデータ"),
  );

  return (
    <section className="rounded-lg border border-slate-700 bg-slate-800/40 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-bold text-slate-200">データ鮮度・反映状態</h3>
          <p className="mt-1 text-xs text-slate-400">
            試合予測に使う基礎データが、どこまで実結果・公式プロフィール・鮮度ポリシーに沿っているかを表示します。
          </p>
        </div>
        <span
          className={`rounded px-2 py-1 text-[10px] font-semibold ${
            summary.freshness_status === "ok" ? "bg-emerald-500/15 text-emerald-300" : "bg-amber-500/15 text-amber-300"
          }`}
        >
          {FRESHNESS_LABELS[summary.freshness_status] ?? summary.freshness_status}
        </span>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-2 md:grid-cols-4">
        <Metric
          label="実結果反映"
          value={`${summary.real_group_match_count}/${summary.real_group_match_expected}`}
          tone={realResultTone}
        />
        <Metric label="決勝T実結果" value={`${summary.real_knockout_match_count}試合`} tone="good" />
        <Metric label="公式プロフィール" value={`${summary.official_profile_coverage_pct.toFixed(1)}%`} tone={officialCoverageTone} />
        <Metric label="未対応シード選手" value={summary.remaining_unmatched_seed_players ?? "-"} tone={summary.remaining_unmatched_seed_players ? "warn" : "good"} />
        <Metric label="鮮度重大" value={summary.freshness_critical_count} tone={summary.freshness_critical_count > 0 ? "warn" : "good"} />
        <Metric label="鮮度注意" value={summary.freshness_warning_count} tone={summary.freshness_warning_count > 0 ? "warn" : "good"} />
        <Metric label="文字監査" value={summary.control_character_issues === 0 ? "異常なし" : `${summary.control_character_issues}件`} tone={summary.control_character_issues === 0 ? "good" : "warn"} />
        <Metric label="seed最終更新" value={formatDate(summary.last_seed_update)} />
      </div>

      {highValueNotes.length > 0 && (
        <div className="mt-3 rounded border border-amber-500/25 bg-amber-500/10 p-3">
          <p className="text-[11px] font-semibold text-amber-200">精度改善前に再確認する点</p>
          <div className="mt-2 space-y-1 text-[11px] text-amber-100/85">
            {highValueNotes.map((note) => (
              <p key={note}>・{note}</p>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
