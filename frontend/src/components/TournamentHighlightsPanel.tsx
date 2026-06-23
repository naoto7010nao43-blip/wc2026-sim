import type { ReactNode } from "react";
import type { MatchSummary, TournamentResult } from "../types/domain";
import { MatchCard } from "./MatchCard";
import { TeamBadge } from "./TeamBadge";

interface Props {
  result: TournamentResult;
}

function allMatches(result: TournamentResult): MatchSummary[] {
  return Object.values(result.matches).flat();
}

function matchWinner(match: MatchSummary): string | null {
  if (match.home_score > match.away_score) return match.home_team_id;
  if (match.away_score > match.home_score) return match.away_team_id;
  if (!match.went_to_penalties || match.penalty_home_score == null || match.penalty_away_score == null) return null;
  return match.penalty_home_score > match.penalty_away_score ? match.home_team_id : match.away_team_id;
}

function matchLoser(match: MatchSummary): string | null {
  const winner = matchWinner(match);
  if (!winner) return null;
  return winner === match.home_team_id ? match.away_team_id : match.home_team_id;
}

function goalTotal(match: MatchSummary): number {
  return match.home_score + match.away_score;
}

function goalMargin(match: MatchSummary): number {
  return Math.abs(match.home_score - match.away_score);
}

function topMatch(matches: MatchSummary[], score: (match: MatchSummary) => number): MatchSummary | null {
  return [...matches].sort((a, b) => score(b) - score(a))[0] ?? null;
}

export function TournamentHighlightsPanel({ result }: Props) {
  const matches = allMatches(result).filter((match) => match.status === "completed");
  const final = result.matches.FINAL?.[0] ?? null;
  const finalist = final ? matchLoser(final) : null;
  const highestScoring = topMatch(matches, goalTotal);
  const biggestMargin = topMatch(matches, goalMargin);
  const shootouts = matches.filter((match) => match.went_to_penalties).length;
  const realMatches = matches.filter((match) => match.is_real).length;

  return (
    <section className="rounded-xl border border-slate-700 bg-slate-800/40 p-5">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-xs uppercase tracking-widest text-slate-500">大会ハイライト</p>
          <h3 className="mt-1 text-lg font-bold text-slate-100">結果の見どころ</h3>
        </div>
        <p className="text-xs text-slate-500">{matches.length}試合集計</p>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <HighlightCard label="優勝" value={result.champion_team_id ? <TeamBadge teamId={result.champion_team_id} /> : "-"} emphasis />
        <HighlightCard label="準優勝" value={finalist ? <TeamBadge teamId={finalist} /> : "-"} />
        <HighlightCard label="PK戦" value={`${shootouts}試合`} />
        <HighlightCard label="実結果反映" value={`${realMatches}/${matches.length}試合`} />
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <MatchHighlight title="最多得点試合" description={highestScoring ? `${goalTotal(highestScoring)}得点` : "-"} match={highestScoring} />
        <MatchHighlight title="最大点差試合" description={biggestMargin ? `${goalMargin(biggestMargin)}点差` : "-"} match={biggestMargin} />
      </div>
    </section>
  );
}

function HighlightCard({ label, value, emphasis = false }: { label: string; value: ReactNode; emphasis?: boolean }) {
  return (
    <div className={`rounded-lg border p-3 ${emphasis ? "border-amber-500/50 bg-amber-500/10" : "border-slate-700/80 bg-slate-900/45"}`}>
      <p className="text-xs text-slate-500">{label}</p>
      <div className={`mt-2 text-sm font-semibold ${emphasis ? "text-amber-200" : "text-slate-100"}`}>{value}</div>
    </div>
  );
}

function MatchHighlight({ title, description, match }: { title: string; description: string; match: MatchSummary | null }) {
  return (
    <div className="rounded-lg border border-slate-700/80 bg-slate-900/45 p-3">
      <div className="mb-2 flex items-center justify-between gap-3">
        <p className="text-xs font-semibold text-slate-300">{title}</p>
        <span className="text-xs text-slate-500">{description}</span>
      </div>
      {match ? <MatchCard match={match} className="bg-slate-800/70" /> : <p className="text-sm text-slate-500">該当試合なし</p>}
    </div>
  );
}
