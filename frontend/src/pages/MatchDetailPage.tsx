import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api/client";
import { MatchEventTimeline } from "../components/MatchEventTimeline";
import { PitchFormationView } from "../components/PitchFormationView";
import { PlayerRatingsPanel } from "../components/PlayerRatingsPanel";
import { TeamBadge } from "../components/TeamBadge";
import type { MatchResult, RoundName } from "../types/domain";

const ROUND_LABELS: Record<RoundName, string> = {
  group: "グループステージ",
  R32: "ラウンド32",
  R16: "ラウンド16",
  QF: "準々決勝",
  SF: "準決勝",
  THIRD_PLACE: "3位決定戦",
  FINAL: "決勝",
};

const PLAYBACK_INTERVAL_MS = 350;

function ratio(home: number | null, away: number | null): number {
  const h = home ?? 0;
  const a = away ?? 0;
  if (h + a === 0) return 50;
  return (100 * h) / (h + a);
}

function fmt(value: number | null): string {
  return value == null ? "-" : String(value);
}

function StatRow({ label, home, away, homePct }: { label: string; home: string; away: string; homePct: number }) {
  return (
    <div>
      <div className="flex items-center justify-between">
        <span className="w-10 text-right font-semibold text-slate-100">{home}</span>
        <span className="text-slate-500">{label}</span>
        <span className="w-10 text-left font-semibold text-slate-100">{away}</span>
      </div>
      <div className="mt-0.5 flex h-1 overflow-hidden rounded-full bg-slate-700">
        <div className="bg-blue-400" style={{ width: `${homePct}%` }} />
        <div className="bg-rose-400" style={{ width: `${100 - homePct}%` }} />
      </div>
    </div>
  );
}

export function MatchDetailPage() {
  const { matchId } = useParams<{ matchId: string }>();
  const [match, setMatch] = useState<MatchResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!matchId) return;
    setMatch(null);
    api
      .getMatch(matchId)
      .then((m) => {
        setMatch(m);
        setCurrentIndex(m.events.length - 1);
        setIsPlaying(false);
      })
      .catch((e) => setError(String(e)));
  }, [matchId]);

  useEffect(() => {
    if (!isPlaying || !match) return;
    timerRef.current = setInterval(() => {
      setCurrentIndex((idx) => {
        if (idx >= match.events.length - 1) {
          setIsPlaying(false);
          return idx;
        }
        return idx + 1;
      });
    }, PLAYBACK_INTERVAL_MS);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isPlaying, match]);

  if (error) return <p className="text-rose-400">{error}</p>;
  if (!match) return <p className="text-slate-400">読み込み中...</p>;

  const isAtEnd = currentIndex >= match.events.length - 1;

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-slate-700 bg-slate-800/40 p-4">
        <div className="flex items-center justify-center gap-2">
          <p className="text-xs uppercase tracking-widest text-emerald-400">{ROUND_LABELS[match.round]}</p>
          {match.is_real ? (
            <span className="rounded bg-amber-500/20 px-1.5 py-0.5 text-[10px] font-semibold text-amber-400">実結果</span>
          ) : (
            <span className="rounded bg-slate-700 px-1.5 py-0.5 text-[10px] text-slate-400">シミュレーション予測</span>
          )}
        </div>
        <div className="mt-1 flex items-center justify-center gap-4 text-2xl font-bold">
          <TeamBadge teamId={match.home_team_id} />
          <span>
            {match.home_score} - {match.away_score}
          </span>
          <TeamBadge teamId={match.away_team_id} />
        </div>
        {match.went_to_penalties && (
          <p className="mt-1 text-center text-sm text-amber-400">
            PK戦 {match.penalty_home_score} - {match.penalty_away_score}
          </p>
        )}
        {match.is_real ? (
          <p className="mt-2 text-center text-xs text-slate-500">出典: {match.data_source}</p>
        ) : (
          <p className="mt-2 text-center text-sm text-slate-400">
            フォーメーション: {match.home_formation} vs {match.away_formation}
          </p>
        )}
        {match.home_possession_pct != null && (
          <div className="mx-auto mt-3 max-w-md space-y-1.5 text-xs text-slate-300">
            <StatRow label="ボール保持率" home={`${match.home_possession_pct}%`} away={`${match.away_possession_pct}%`} homePct={match.home_possession_pct} />
            <StatRow label="シュート" home={fmt(match.home_shots)} away={fmt(match.away_shots)} homePct={ratio(match.home_shots, match.away_shots)} />
            {(match.home_shots_on_target != null || match.away_shots_on_target != null) && (
              <StatRow label="枠内シュート" home={fmt(match.home_shots_on_target)} away={fmt(match.away_shots_on_target)} homePct={ratio(match.home_shots_on_target, match.away_shots_on_target)} />
            )}
            {(match.home_yellow_cards != null || match.away_yellow_cards != null) && (
              <StatRow label="イエローカード" home={fmt(match.home_yellow_cards)} away={fmt(match.away_yellow_cards)} homePct={ratio(match.home_yellow_cards, match.away_yellow_cards)} />
            )}
            {((match.home_red_cards ?? 0) > 0 || (match.away_red_cards ?? 0) > 0) && (
              <StatRow label="レッドカード" home={fmt(match.home_red_cards)} away={fmt(match.away_red_cards)} homePct={ratio(match.home_red_cards, match.away_red_cards)} />
            )}
          </div>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-3 rounded-xl border border-slate-700 bg-slate-800/40 p-3">
        <button
          onClick={() => {
            if (isAtEnd) setCurrentIndex(0);
            setIsPlaying((p) => !p || isAtEnd);
          }}
          className="rounded-md bg-emerald-600 px-4 py-1.5 text-sm font-semibold text-white hover:bg-emerald-500"
        >
          {isPlaying ? "一時停止" : isAtEnd ? "最初から再生" : "再生"}
        </button>
        <button
          onClick={() => {
            setIsPlaying(false);
            setCurrentIndex(0);
          }}
          className="rounded-md border border-slate-600 px-3 py-1.5 text-sm text-slate-300 hover:bg-slate-700"
        >
          最初に戻る
        </button>
        <input
          type="range"
          min={0}
          max={Math.max(match.events.length - 1, 0)}
          value={currentIndex}
          onChange={(e) => {
            setIsPlaying(false);
            setCurrentIndex(Number(e.target.value));
          }}
          className="min-w-[160px] flex-1"
        />
        <span className="w-16 shrink-0 text-right text-sm text-slate-400">{match.events[currentIndex]?.minute ?? 0}'</span>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[380px_1fr]">
        {match.home_lineup.length > 0 ? (
          <PitchFormationView
            events={match.events}
            homeTeamId={match.home_team_id}
            awayTeamId={match.away_team_id}
            homeLineup={match.home_lineup}
            awayLineup={match.away_lineup}
            upToIndex={currentIndex}
          />
        ) : (
          <div className="flex items-center justify-center rounded-lg border border-slate-700 bg-slate-800/40 p-4 text-center text-xs text-slate-500">
            実際の試合のため、フォーメーション情報は表示されません。
          </div>
        )}
        <MatchEventTimeline
          events={match.events}
          currentIndex={currentIndex}
          onSelectEvent={(idx) => {
            setIsPlaying(false);
            setCurrentIndex(idx);
          }}
        />
      </div>

      <PlayerRatingsPanel ratings={match.player_ratings} homeTeamId={match.home_team_id} awayTeamId={match.away_team_id} />
    </div>
  );
}
