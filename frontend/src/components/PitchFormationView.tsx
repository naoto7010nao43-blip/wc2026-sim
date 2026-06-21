import type { LineupPlayer, MatchEvent } from "../types/domain";

interface Props {
  events: MatchEvent[];
  homeTeamId: string;
  awayTeamId: string;
  homeLineup: LineupPlayer[];
  awayLineup: LineupPlayer[];
  upToIndex?: number;
}

const HOME_COLOR = "#60a5fa";
const AWAY_COLOR = "#fb7185";
const BALL_TRAIL_LENGTH = 6;

const ACTION_LABELS: Record<string, string> = {
  goal: "ゴール!",
  shot: "シュート",
  key_pass: "決定的なパス",
  tackle: "タックル",
  yellow_card: "イエローカード",
  penalty_kick: "PK",
  substitution: "選手交代",
};

function findPlayer(lineup: LineupPlayer[], playerId: string | null): LineupPlayer | undefined {
  if (!playerId) return undefined;
  return lineup.find((p) => p.player_id === playerId);
}

export function PitchFormationView({ events, homeTeamId, homeLineup, awayLineup, upToIndex }: Props) {
  const currentIdx = upToIndex ?? events.length - 1;
  const current = events[currentIdx];

  const trail = events
    .slice(Math.max(0, currentIdx - BALL_TRAIL_LENGTH + 1), currentIdx + 1)
    .filter((e) => e.x != null && e.y != null);
  const ball = trail[trail.length - 1] ?? { x: 50, y: 50 };

  const isHome = current?.team_id === homeTeamId;
  const primary = current
    ? findPlayer(isHome ? homeLineup : awayLineup, current.player_id) ?? findPlayer(isHome ? awayLineup : homeLineup, current.player_id)
    : undefined;
  const secondary = current
    ? findPlayer(isHome ? awayLineup : homeLineup, current.secondary_player_id) ?? findPlayer(isHome ? homeLineup : awayLineup, current.secondary_player_id)
    : undefined;
  const primaryPos = current?.x != null && current?.y != null ? { x: current.x, y: current.y } : primary;
  const actionLabel = current ? ACTION_LABELS[current.event_type] : undefined;

  return (
    <div className="space-y-2">
      <div className="relative aspect-[1.4] w-full overflow-hidden rounded-lg">
        <svg viewBox="0 0 100 100" className="absolute inset-0 h-full w-full" preserveAspectRatio="none">
          <rect x="0" y="0" width="100" height="100" fill="#166534" />
          <rect x="0" y="0" width="100" height="100" fill="url(#stripes)" opacity="0.06" />
          <defs>
            <pattern id="stripes" width="10" height="100" patternUnits="userSpaceOnUse">
              <rect width="5" height="100" fill="white" />
            </pattern>
          </defs>
          <rect x="0.5" y="0.5" width="99" height="99" fill="none" stroke="white" strokeWidth="0.5" />
          <line x1="50" y1="0" x2="50" y2="100" stroke="white" strokeWidth="0.3" />
          <circle cx="50" cy="50" r="8" fill="none" stroke="white" strokeWidth="0.3" />
          <rect x="0" y="25" width="12" height="50" fill="none" stroke="white" strokeWidth="0.3" />
          <rect x="88" y="25" width="12" height="50" fill="none" stroke="white" strokeWidth="0.3" />

          {/* Static formation shape for every player not currently involved in the action. */}
          {homeLineup.map((p) => (
            <circle key={p.player_id} cx={p.x} cy={p.y} r={1.3} fill={HOME_COLOR} opacity={primary?.player_id === p.player_id ? 0 : 0.5} />
          ))}
          {awayLineup.map((p) => (
            <circle key={p.player_id} cx={p.x} cy={p.y} r={1.3} fill={AWAY_COLOR} opacity={primary?.player_id === p.player_id ? 0 : 0.5} />
          ))}

          {/* Connector between the two players involved in the current action. */}
          {primaryPos && secondary && (
            <line
              x1={primaryPos.x} y1={primaryPos.y} x2={secondary.x} y2={secondary.y}
              stroke="white" strokeWidth="0.4" strokeDasharray="1.5,1" opacity="0.8"
            />
          )}

          {secondary && (
            <circle cx={secondary.x} cy={secondary.y} r={2} fill={isHome ? AWAY_COLOR : HOME_COLOR} stroke="white" strokeWidth="0.4" />
          )}

          {/* Ball trail (fading breadcrumb of the last few touches). */}
          {trail.map((e, idx) => (
            <circle key={idx} cx={e.x ?? 50} cy={e.y ?? 50} r={0.8} fill="white" opacity={0.15 + 0.5 * (idx / trail.length)} />
          ))}

          {/* The actively-involved player, highlighted and pulsing. */}
          {primaryPos && (
            <circle cx={primaryPos.x} cy={primaryPos.y} r={2.4} fill={isHome ? HOME_COLOR : AWAY_COLOR} stroke="white" strokeWidth="0.5">
              <animate attributeName="r" values="2.4;3.2;2.4" dur="1s" repeatCount="indefinite" />
            </circle>
          )}

          {/* The ball itself: bright, distinct, always on top. */}
          <circle cx={ball.x ?? 50} cy={ball.y ?? 50} r={1.1} fill="white" stroke="#0f172a" strokeWidth="0.4" />
        </svg>

        {primaryPos && primary && (
          <div
            className="pointer-events-none absolute -translate-x-1/2 -translate-y-full rounded bg-slate-900/90 px-1.5 py-0.5 text-[11px] font-bold whitespace-nowrap text-white shadow"
            style={{ left: `${primaryPos.x}%`, top: `${primaryPos.y - 3}%` }}
          >
            {primary.name}
          </div>
        )}
        {secondary && (
          <div
            className="pointer-events-none absolute -translate-x-1/2 rounded bg-slate-900/80 px-1.5 py-0.5 text-[10px] text-slate-200 whitespace-nowrap shadow"
            style={{ left: `${secondary.x}%`, top: `${secondary.y + 3}%` }}
          >
            {secondary.name}
          </div>
        )}
      </div>

      <div className="flex items-center justify-between text-xs text-slate-400">
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ backgroundColor: HOME_COLOR }} />
          ホーム
          <span className="ml-3 inline-block h-2.5 w-2.5 rounded-full" style={{ backgroundColor: AWAY_COLOR }} />
          アウェイ
        </span>
        {actionLabel && <span className="font-semibold text-slate-200">{actionLabel}</span>}
      </div>
    </div>
  );
}
