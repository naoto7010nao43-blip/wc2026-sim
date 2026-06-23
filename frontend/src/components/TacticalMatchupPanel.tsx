import type { TeamSummary, TacticalProfile } from "../types/domain";
import { TeamBadge } from "./TeamBadge";

interface Props {
  homeTeam: TeamSummary | undefined;
  awayTeam: TeamSummary | undefined;
}

type AxisKey = "press_intensity" | "possession_style" | "defensive_line_height";

const AXES: { key: AxisKey; label: string }[] = [
  { key: "press_intensity", label: "プレス" },
  { key: "possession_style", label: "保持" },
  { key: "defensive_line_height", label: "ライン" },
];

function score(profile: TacticalProfile | null | undefined, key: AxisKey): number {
  return Math.max(0, Math.min(100, profile?.[key] ?? 50));
}

function edgeLabel(value: number): string {
  if (value >= 14) return "強く優位";
  if (value >= 6) return "やや優位";
  if (value <= -14) return "強く不利";
  if (value <= -6) return "やや不利";
  return "互角";
}

function pressMatchup(profile: TacticalProfile, opponent: TacticalProfile): number {
  return Math.round((profile.press_intensity - opponent.possession_style + profile.press_intensity - opponent.defensive_line_height) / 2);
}

export function TacticalMatchupPanel({ homeTeam, awayTeam }: Props) {
  if (!homeTeam || !awayTeam || homeTeam.id === awayTeam.id) return null;
  if (!homeTeam.tactical_profile || !awayTeam.tactical_profile) return null;

  const homeEdge = pressMatchup(homeTeam.tactical_profile, awayTeam.tactical_profile);
  const awayEdge = pressMatchup(awayTeam.tactical_profile, homeTeam.tactical_profile);

  return (
    <section className="rounded-xl border border-slate-700 bg-slate-800/40 p-4">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-xs uppercase tracking-widest text-slate-500">戦術相性</p>
          <h3 className="mt-1 text-base font-bold text-slate-100">監督プラン比較</h3>
        </div>
        <p className="text-xs text-slate-500">
          プレス強度、保持志向、最終ラインの噛み合わせを試合前に確認します。
        </p>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-[1fr_auto_1fr]">
        <TeamTacticalColumn team={homeTeam} edge={homeEdge} />
        <div className="hidden items-center justify-center text-xs text-slate-500 lg:flex">vs</div>
        <TeamTacticalColumn team={awayTeam} edge={awayEdge} alignRight />
      </div>

      <p className="mt-4 text-[11px] leading-relaxed text-slate-500">
        予測モデルでは、プレス強度が相手の保持志向・守備ラインと噛み合う場合に期待得点へ小さな補正が入ります。
        ここでは試合前にその見どころを読めるよう、同じ3軸を可視化しています。
      </p>
    </section>
  );
}

function TeamTacticalColumn({ team, edge, alignRight = false }: { team: TeamSummary; edge: number; alignRight?: boolean }) {
  const profile = team.tactical_profile;
  if (!profile) return null;

  return (
    <div className="min-w-0">
      <div className={`flex items-center gap-2 ${alignRight ? "lg:justify-end" : ""}`}>
        <TeamBadge teamId={team.id} />
        <span className="truncate text-xs text-slate-500">{profile.manager_name}</span>
      </div>

      <div className="mt-3 space-y-2">
        {AXES.map((axis) => {
          const value = score(profile, axis.key);
          return (
            <div key={axis.key}>
              <div className="flex items-center justify-between text-[11px] text-slate-400">
                <span>{axis.label}</span>
                <span className="font-semibold text-slate-200">{value}</span>
              </div>
              <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-slate-700">
                <div className="h-full rounded-full bg-emerald-500" style={{ width: `${value}%` }} />
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-3 rounded-lg border border-slate-700/80 bg-slate-900/45 px-3 py-2 text-xs">
        <span className="text-slate-500">プレス相性: </span>
        <span className={edge >= 6 ? "font-semibold text-emerald-300" : edge <= -6 ? "font-semibold text-rose-300" : "font-semibold text-slate-200"}>
          {edgeLabel(edge)}
        </span>
      </div>
    </div>
  );
}

