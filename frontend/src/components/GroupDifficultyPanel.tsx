import { useEffect, useState } from "react";
import { api } from "../api/client";
import { TeamBadge } from "./TeamBadge";
import type { GroupDifficulty, TournamentGroupDifficultyOut } from "../types/domain";

const BAND_LABEL: Record<GroupDifficulty["difficulty_band"], string> = {
  high: "高",
  medium: "中",
  low: "低",
};

const BAND_CLASS: Record<GroupDifficulty["difficulty_band"], string> = {
  high: "border-rose-500/50 bg-rose-950/20 text-rose-200",
  medium: "border-amber-500/45 bg-amber-950/20 text-amber-200",
  low: "border-slate-600 bg-slate-900/45 text-slate-200",
};

export function GroupDifficultyPanel() {
  const [summary, setSummary] = useState<TournamentGroupDifficultyOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .getTournamentGroupDifficulty()
      .then((data) => {
        if (!cancelled) setSummary(data);
      })
      .catch((e) => {
        if (!cancelled) setError(String(e));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <section className="rounded-xl border border-slate-700 bg-slate-800/40 p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-lg font-bold">死の組メーター</h3>
          <p className="mt-1 max-w-3xl text-sm leading-relaxed text-slate-400">
            各グループの平均戦力、勝率差の小ささ、引き分けや波乱の起きやすさを合わせて、通過争いの厳しさを比較します。
          </p>
        </div>
        {summary && (
          <div className="rounded-lg border border-slate-700 bg-slate-900/55 px-3 py-2 text-right">
            <p className="text-[11px] text-slate-500">比較対象</p>
            <p className="text-base font-bold text-slate-100">{summary.group_count}組</p>
          </div>
        )}
      </div>

      {loading && <p className="mt-4 text-sm text-slate-400">グループ難度を計算中...</p>}
      {error && <p className="mt-4 text-sm text-rose-400">グループ難度の取得に失敗しました: {error}</p>}

      {summary && (
        <div className="mt-5 space-y-3">
          {summary.groups.slice(0, 6).map((group, index) => (
            <GroupDifficultyCard key={group.group_id} group={group} rank={index + 1} />
          ))}
          <p className="text-[11px] leading-relaxed text-slate-500">
            難度スコアは予測モデル由来の比較指標です。モデル: {summary.model_version}。{summary.disclaimer}
          </p>
        </div>
      )}
    </section>
  );
}

function GroupDifficultyCard({ group, rank }: { group: GroupDifficulty; rank: number }) {
  return (
    <article className={`rounded-lg border p-3 ${BAND_CLASS[group.difficulty_band]}`}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest opacity-75">#{rank} / Group {group.group_id}</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {group.teams.map((team) => (
              <TeamBadge key={team.team_id} teamId={team.team_id} />
            ))}
          </div>
        </div>
        <div className="grid grid-cols-3 gap-2 text-right text-xs sm:min-w-[320px]">
          <Metric label="難度" value={group.difficulty_score.toFixed(1)} />
          <Metric label="本命差" value={`${group.average_favorite_gap_pct.toFixed(1)}pt`} />
          <Metric label="波乱圧" value={group.upset_pressure.toFixed(1)} />
        </div>
      </div>
      <div className="mt-3 grid grid-cols-1 gap-2 text-xs leading-relaxed md:grid-cols-[1fr_1fr_2fr]">
        <p>判定: <span className="font-semibold">難度{BAND_LABEL[group.difficulty_band]}</span></p>
        <p>平均戦力 {group.average_strength.toFixed(1)} / 戦力幅 {group.strength_spread.toFixed(1)}</p>
        <p>{group.reason_ja}</p>
      </div>
    </article>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[11px] opacity-70">{label}</p>
      <p className="mt-0.5 text-sm font-bold">{value}</p>
    </div>
  );
}
