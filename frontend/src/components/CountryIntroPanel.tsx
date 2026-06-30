import { Link } from "react-router-dom";
import type { PlayerSummary, TeamOut } from "../types/domain";
import { TeamBadge } from "./TeamBadge";

// Confederation -> Japanese label. These are factual organisational names,
// not fabricated; an unknown code falls back to the raw value.
const CONFEDERATION_JA: Record<string, string> = {
  UEFA: "欧州 (UEFA)",
  CONMEBOL: "南米 (CONMEBOL)",
  CONCACAF: "北中米カリブ (CONCACAF)",
  CAF: "アフリカ (CAF)",
  AFC: "アジア (AFC)",
  OFC: "オセアニア (OFC)",
};

function band(value: number, low: string, mid: string, high: string): string {
  if (value >= 70) return high;
  if (value <= 40) return low;
  return mid;
}

// One-line playstyle description derived purely from the team's tactical
// profile (the same numbers the prediction model uses). No external claims.
function playstyle(team: TeamOut): string {
  const p = team.tactical_profile;
  if (!p) return "戦術プロファイル未登録";
  return [
    band(p.press_intensity, "自陣で構える守備", "状況対応のプレス", "高い位置からのプレス"),
    band(p.possession_style, "縦に速い攻撃", "保持と速攻を併用", "ボール保持で主導"),
  ].join(" / ");
}

function keyPlayers(players: PlayerSummary[], count = 4): PlayerSummary[] {
  return [...players].sort((a, b) => b.overall - a.overall).slice(0, count);
}

function TeamIntro({ team }: { team: TeamOut }) {
  const profile = team.tactical_profile;
  const players = keyPlayers(team.players);
  return (
    <div className="flex-1 rounded-lg border border-slate-700/80 bg-slate-900/45 p-3">
      <div className="flex items-center justify-between gap-2">
        <Link to={`/teams/${team.id}`} className="flex items-center gap-2 hover:opacity-80">
          <TeamBadge teamId={team.id} />
        </Link>
        <span className="rounded bg-slate-700 px-1.5 py-0.5 text-[10px] text-slate-300">
          {CONFEDERATION_JA[team.confederation] ?? team.confederation}
        </span>
      </div>

      <dl className="mt-2 space-y-0.5 text-[11px] text-slate-400">
        <div className="flex justify-between">
          <dt>FIFAランク</dt>
          <dd className="font-semibold text-slate-200">{team.fifa_rank != null ? `${team.fifa_rank}位` : "-"}</dd>
        </div>
        <div className="flex justify-between">
          <dt>監督</dt>
          <dd className="font-semibold text-slate-200">{profile?.manager_name ?? "-"}</dd>
        </div>
        <div className="flex justify-between">
          <dt>フォーメーション</dt>
          <dd className="font-semibold text-slate-200">{team.default_formation}</dd>
        </div>
      </dl>

      <p className="mt-2 rounded bg-slate-800/60 px-2 py-1 text-[11px] leading-relaxed text-slate-300">
        {playstyle(team)}
      </p>

      <p className="mt-2 text-[10px] uppercase tracking-widest text-slate-500">注目選手</p>
      <ul className="mt-1 space-y-1">
        {players.map((p) => (
          <li key={p.id} className="flex items-center justify-between gap-2 text-[11px]">
            <span className="truncate text-slate-200">
              {p.name_ja ?? p.name}
              <span className="ml-1 text-slate-500">{p.primary_position}</span>
            </span>
            <span className="flex shrink-0 items-center gap-1.5 text-slate-400">
              {p.club_name && <span className="hidden max-w-[88px] truncate sm:inline">{p.club_name}</span>}
              <span className="rounded bg-emerald-500/15 px-1 font-semibold text-emerald-300">{p.overall}</span>
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/**
 * "Get to know the two nations" panel for the match screen — aimed at viewers
 * unfamiliar with these teams. Every figure is derived from the app's own
 * dataset (FIFA rank, confederation, manager, tactical profile, player
 * ratings); nothing is fabricated or presented as sourced real-world prose.
 */
export function CountryIntroPanel({ home, away }: { home: TeamOut; away: TeamOut }) {
  return (
    <section className="rounded-xl border border-slate-700 bg-slate-800/40 p-4">
      <p className="text-xs uppercase tracking-widest text-slate-500">対戦国ガイド</p>
      <p className="mt-0.5 text-[11px] text-slate-500">
        両国の基本データ・戦術スタイル・注目選手をまとめました（数値は本アプリのデータに基づく推定です）。
      </p>
      <div className="mt-3 flex flex-col gap-3 sm:flex-row">
        <TeamIntro team={home} />
        <TeamIntro team={away} />
      </div>
    </section>
  );
}
