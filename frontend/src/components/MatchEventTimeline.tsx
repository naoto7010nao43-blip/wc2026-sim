import { useEffect, useRef } from "react";
import type { MatchEvent } from "../types/domain";

interface Props {
  events: MatchEvent[];
  currentIndex?: number;
  onSelectEvent?: (index: number) => void;
}

const EVENT_ICONS: Record<string, string> = {
  goal: "⚽",
  shot: "🎯",
  key_pass: "🔑",
  tackle: "🛡️",
  yellow_card: "🟨",
  red_card: "🟥",
  substitution: "🔁",
  kickoff: "🏁",
  halftime: "⏸️",
  extra_time_start: "⏱️",
  extra_time_halftime: "⏸️",
  fulltime: "🏆",
  penalty_kick: "🥅",
  shootout_winner: "🏆",
};

export function MatchEventTimeline({ events, currentIndex, onSelectEvent }: Props) {
  const activeRef = useRef<HTMLLIElement | null>(null);

  useEffect(() => {
    activeRef.current?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [currentIndex]);

  if (events.length === 0) {
    return (
      <div className="flex max-h-[480px] items-center justify-center rounded-lg border border-slate-700 bg-slate-800/60 p-4 text-center text-xs text-slate-500">
        この試合のイベント再現は利用できません。
      </div>
    );
  }

  return (
    <ol className="max-h-[480px] list-none space-y-0.5 overflow-y-auto rounded-lg border border-slate-700 bg-slate-800/60 p-2">
      {events.map((e, idx) => {
        const isActive = idx === currentIndex;
        const isPast = currentIndex != null && idx <= currentIndex;
        return (
          <li
            key={idx}
            ref={isActive ? activeRef : undefined}
            onClick={() => onSelectEvent?.(idx)}
            className={`flex items-baseline gap-2 rounded px-2 py-1 text-sm ${onSelectEvent ? "cursor-pointer" : ""} ${
              isActive ? "bg-emerald-700/40 text-slate-100" : isPast ? "text-slate-300" : "text-slate-500"
            } ${e.event_type === "goal" || (e.event_type === "penalty_kick" && e.event_metadata?.scored) ? "font-bold text-amber-400" : ""}`}
          >
            <span className="w-9 shrink-0 font-mono text-xs text-slate-500">{e.minute}'</span>
            <span>{EVENT_ICONS[e.event_type] ?? "•"}</span>
            <span>{e.description}</span>
          </li>
        );
      })}
    </ol>
  );
}
