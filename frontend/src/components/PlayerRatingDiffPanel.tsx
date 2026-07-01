import type { PlayerRatingDiffSummary } from "../types/domain";

interface Props {
  summary: PlayerRatingDiffSummary;
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

function ChangeList({ title, rows }: { title: string; rows: Array<Record<string, number | string | null>> }) {
  if (rows.length === 0) {
    return (
      <div>
        <p className="text-[11px] font-semibold text-slate-300">{title}</p>
        <p className="mt-1 text-[11px] text-slate-500">大きな差分はありません。</p>
      </div>
    );
  }

  return (
    <div>
      <p className="text-[11px] font-semibold text-slate-300">{title}</p>
      <div className="mt-1 grid grid-cols-1 gap-1 sm:grid-cols-2">
        {rows.slice(0, 6).map((row) => (
          <div key={`${row.playerId}-${row.from}-${row.to}`} className="rounded bg-slate-900/45 px-2 py-1 text-[11px] text-slate-300">
            <span className="font-semibold text-slate-200">{row.playerId}</span>
            <span className="ml-2 text-slate-500">
              {row.from ?? "-"} → {row.to ?? "-"}
            </span>
            <span className="ml-2 text-emerald-300">{Number(row.delta ?? 0) > 0 ? "+" : ""}{row.delta}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function IdPills({ ids }: { ids: string[] }) {
  if (ids.length === 0) {
    return <p className="text-[11px] text-slate-500">対象はありません。</p>;
  }
  return (
    <div className="flex flex-wrap gap-1.5">
      {ids.slice(0, 12).map((id) => (
        <span key={id} className="rounded bg-slate-900/60 px-1.5 py-0.5 text-[11px] text-slate-300">
          {id}
        </span>
      ))}
    </div>
  );
}

export function PlayerRatingDiffPanel({ summary }: Props) {
  if (summary.totalPlayers === 0) {
    return (
      <div className="rounded-lg border border-slate-700 bg-slate-800/40 p-4 text-center text-sm text-slate-400">{summary.note}</div>
    );
  }

  const hasDataRisk = summary.lowConfidencePlayerCount > 0 || summary.missingCriticalDataCount > 0;

  return (
    <div className="space-y-3 rounded-lg border border-slate-700 bg-slate-800/40 p-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-bold text-slate-200">能力値差分監査</h3>
          <p className="mt-1 text-xs text-slate-400">
            生成済みの能力値レポートから、手動補正・外部出典・信頼度の確認点を読み取り専用で表示します。
          </p>
        </div>
        <span className="rounded bg-slate-700/50 px-2 py-1 text-[10px] text-slate-300">seed未変更</span>
      </div>

      <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
        <Metric label="対象選手" value={summary.totalPlayers} tone="good" />
        <Metric label="手動補正" value={summary.changedByManualOverrideCount} tone={summary.changedByManualOverrideCount > 0 ? "warn" : "good"} />
        <Metric label="外部出典あり" value={summary.externallySourcedCount} tone="slate" />
        <Metric label="EA尺度補正" value={summary.calibratedToEaScaleCount} tone="slate" />
        <Metric label="低信頼度" value={summary.lowConfidencePlayerCount} tone={summary.lowConfidencePlayerCount > 0 ? "warn" : "good"} />
        <Metric label="重要データ欠落" value={summary.missingCriticalDataCount} tone={summary.missingCriticalDataCount > 0 ? "warn" : "good"} />
        <Metric label="上昇差分" value={summary.biggestRisers.length} tone={summary.biggestRisers.length > 0 ? "warn" : "good"} />
        <Metric label="下降差分" value={summary.biggestFallers.length} tone={summary.biggestFallers.length > 0 ? "warn" : "good"} />
      </div>

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
        <ChangeList title="主な上昇差分" rows={summary.biggestRisers} />
        <ChangeList title="主な下降差分" rows={summary.biggestFallers} />
      </div>

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
        <div>
          <p className="text-[11px] font-semibold text-slate-300">手動補正が入った選手</p>
          <div className="mt-1">
            <IdPills ids={summary.changedByManualOverride} />
          </div>
        </div>
        <div>
          <p className="text-[11px] font-semibold text-slate-300">外部出典サンプル</p>
          <div className="mt-1">
            <IdPills ids={summary.externallySourcedSample} />
          </div>
        </div>
      </div>

      {hasDataRisk && (
        <div className="rounded border border-amber-500/30 bg-amber-500/10 p-3 text-[11px] text-amber-100">
          低信頼度または重要データ欠落が残っています。能力値の調整より先に、基礎データと出典の確認を優先してください。
        </div>
      )}

      <div className="rounded border border-slate-700/70 bg-slate-900/40 p-3">
        <p className="text-[11px] font-semibold text-slate-300">確認方針</p>
        <ul className="mt-2 space-y-1 text-[11px] text-slate-400">
          {summary.recommendationsJa.map((item) => (
            <li key={item}>・{item}</li>
          ))}
        </ul>
      </div>

      <p className="text-[11px] text-slate-500">{summary.note}</p>
    </div>
  );
}
