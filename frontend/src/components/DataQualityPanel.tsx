import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { DataQualitySummary } from "../types/domain";

function formatDate(value: string | null): string {
  if (!value) return "不明";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "不明";
  return date.toLocaleDateString("ja-JP", { year: "numeric", month: "short", day: "numeric" });
}

export function DataQualityPanel() {
  const [summary, setSummary] = useState<DataQualitySummary | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api
      .getDataQualitySummary()
      .then((data) => {
        if (!cancelled) setSummary(data);
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (failed) {
    return (
      <section className="rounded-xl border border-slate-700 bg-slate-800/40 p-4 text-center text-xs text-slate-500">
        データ品質情報は現在表示できません。
      </section>
    );
  }

  if (!summary) {
    return (
      <section className="rounded-xl border border-slate-700 bg-slate-800/40 p-4 text-center text-xs text-slate-500">
        データ品質情報を読み込み中...
      </section>
    );
  }

  return (
    <section className="rounded-xl border border-slate-700 bg-slate-800/40 p-4">
      <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-xs uppercase tracking-widest text-slate-500">データ品質</p>
        <p className="text-[11px] text-slate-500">最終更新: {formatDate(summary.last_seed_update)}</p>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Metric label="公式データ反映率" value={`${summary.official_profile_coverage_pct.toFixed(1)}%`} />
        <Metric
          label="未対応の公式選手"
          value={summary.remaining_unmatched_official_players != null ? `${summary.remaining_unmatched_official_players}人` : "-"}
        />
        <Metric
          label="未対応のシード選手"
          value={summary.remaining_unmatched_seed_players != null ? `${summary.remaining_unmatched_seed_players}人` : "-"}
        />
        <Metric
          label="反映待ちの更新候補"
          value={summary.matched_player_field_update_candidates != null ? `${summary.matched_player_field_update_candidates}件` : "-"}
        />
      </div>

      {summary.notes.length > 0 && (
        <ul className="mt-3 space-y-1 text-[11px] text-slate-500">
          {summary.notes.map((note, idx) => (
            <li key={idx}>・{note}</li>
          ))}
        </ul>
      )}
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[11px] text-slate-500">{label}</p>
      <p className="mt-1 text-sm font-semibold text-slate-100">{value}</p>
    </div>
  );
}
