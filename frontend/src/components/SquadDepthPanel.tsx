import type { PlayerSummary } from "../types/domain";

interface Props {
  players: PlayerSummary[];
}

type PositionGroupKey = "GK" | "DF" | "MF" | "FW";

interface PositionGroup {
  key: PositionGroupKey;
  label: string;
  players: PlayerSummary[];
}

function positionGroup(position: string): PositionGroupKey {
  const p = position.toUpperCase();
  if (p.includes("GK")) return "GK";
  if (p.includes("CB") || p.includes("LB") || p.includes("RB") || p.includes("DF")) return "DF";
  if (p.includes("DM") || p.includes("CM") || p.includes("AM") || p.includes("MF")) return "MF";
  return "FW";
}

function average(values: number[]): number | null {
  if (values.length === 0) return null;
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function formatAverage(value: number | null): string {
  return value == null ? "-" : value.toFixed(1);
}

function strongest(players: PlayerSummary[]): PlayerSummary | null {
  if (players.length === 0) return null;
  return [...players].sort((a, b) => b.overall - a.overall)[0];
}

function coveragePct(players: PlayerSummary[], predicate: (player: PlayerSummary) => boolean): number {
  if (players.length === 0) return 0;
  return Math.round((players.filter(predicate).length / players.length) * 100);
}

function playerLabel(player: PlayerSummary | null): string {
  if (!player) return "-";
  return player.name_ja ?? player.name;
}

function buildGroups(players: PlayerSummary[]): PositionGroup[] {
  const groups: PositionGroup[] = [
    { key: "GK", label: "GK", players: [] },
    { key: "DF", label: "守備", players: [] },
    { key: "MF", label: "中盤", players: [] },
    { key: "FW", label: "攻撃", players: [] },
  ];
  const byKey = new Map(groups.map((group) => [group.key, group]));
  for (const player of players) {
    byKey.get(positionGroup(player.primary_position))?.players.push(player);
  }
  return groups;
}

export function SquadDepthPanel({ players }: Props) {
  const groups = buildGroups(players);
  const topOverall = strongest(players);
  const topCaps = [...players].filter((p) => p.caps != null).sort((a, b) => (b.caps ?? 0) - (a.caps ?? 0))[0] ?? null;
  const topStarter =
    [...players].filter((p) => p.starting_probability != null).sort((a, b) => (b.starting_probability ?? 0) - (a.starting_probability ?? 0))[0] ?? null;

  const ageBands = {
    u23: players.filter((p) => p.age <= 23).length,
    prime: players.filter((p) => p.age >= 24 && p.age <= 30).length,
    veteran: players.filter((p) => p.age >= 31).length,
  };

  const profileCoverage = [
    { label: "クラブ", pct: coveragePct(players, (p) => p.club_name != null) },
    { label: "身長", pct: coveragePct(players, (p) => p.height_cm != null) },
    { label: "生年月日", pct: coveragePct(players, (p) => p.date_of_birth != null) },
    { label: "代表成績", pct: coveragePct(players, (p) => p.caps != null || p.national_team_goals != null) },
  ];

  return (
    <section className="rounded-xl border border-slate-700 bg-slate-800/40 p-4">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-xs uppercase tracking-widest text-slate-500">スカッド分析</p>
          <h2 className="mt-1 text-lg font-bold text-slate-100">選手層・プロフィール充足</h2>
        </div>
        <p className="text-xs text-slate-500">既存の選手評価と公式プロフィール項目から自動集計</p>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-4">
        {groups.map((group) => {
          const avgOverall = average(group.players.map((p) => p.overall));
          const avgStart = average(group.players.map((p) => p.starting_probability ?? 0));
          const best = strongest(group.players);
          return (
            <div key={group.key} className="rounded-lg border border-slate-700/80 bg-slate-900/45 p-3">
              <div className="flex items-center justify-between text-xs">
                <span className="font-semibold text-slate-200">{group.label}</span>
                <span className="text-slate-500">{group.players.length}人</span>
              </div>
              <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
                <div>
                  <p className="text-slate-500">平均能力</p>
                  <p className="text-base font-bold text-slate-100">{formatAverage(avgOverall)}</p>
                </div>
                <div>
                  <p className="text-slate-500">先発濃度</p>
                  <p className="text-base font-bold text-slate-100">{formatAverage(avgStart)}%</p>
                </div>
              </div>
              <p className="mt-3 truncate text-xs text-slate-400">中心: {playerLabel(best)}</p>
            </div>
          );
        })}
      </div>

      <div className="mt-4 grid grid-cols-1 gap-3 lg:grid-cols-3">
        <div className="rounded-lg border border-slate-700/80 bg-slate-900/45 p-3">
          <p className="text-xs font-semibold text-slate-300">年齢構成</p>
          <div className="mt-3 grid grid-cols-3 gap-2 text-center text-xs">
            <AgeTile label="U23" value={ageBands.u23} />
            <AgeTile label="24-30" value={ageBands.prime} />
            <AgeTile label="31+" value={ageBands.veteran} />
          </div>
        </div>

        <div className="rounded-lg border border-slate-700/80 bg-slate-900/45 p-3">
          <p className="text-xs font-semibold text-slate-300">公式プロフィール充足</p>
          <div className="mt-3 space-y-2">
            {profileCoverage.map((item) => (
              <div key={item.label}>
                <div className="flex items-center justify-between text-[11px] text-slate-400">
                  <span>{item.label}</span>
                  <span>{item.pct}%</span>
                </div>
                <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-slate-700">
                  <div className="h-full rounded-full bg-emerald-500" style={{ width: `${item.pct}%` }} />
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-lg border border-slate-700/80 bg-slate-900/45 p-3">
          <p className="text-xs font-semibold text-slate-300">注目指標</p>
          <div className="mt-3 space-y-2 text-xs text-slate-400">
            <MetricRow label="最高評価" value={`${playerLabel(topOverall)} (${topOverall?.overall ?? "-"})`} />
            <MetricRow label="最多代表経験" value={`${playerLabel(topCaps)} (${topCaps?.caps ?? "-"}試合)`} />
            <MetricRow label="先発最有力" value={`${playerLabel(topStarter)} (${topStarter?.starting_probability != null ? Math.round(topStarter.starting_probability) : "-"}%)`} />
          </div>
        </div>
      </div>
    </section>
  );
}

function AgeTile({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md bg-slate-800/80 px-2 py-2">
      <p className="text-[11px] text-slate-500">{label}</p>
      <p className="text-base font-bold text-slate-100">{value}</p>
    </div>
  );
}

function MetricRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="shrink-0 text-slate-500">{label}</span>
      <span className="min-w-0 truncate text-right text-slate-200">{value}</span>
    </div>
  );
}

