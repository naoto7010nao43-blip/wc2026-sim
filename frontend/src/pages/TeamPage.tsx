import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import { LikelyLineupPanel } from "../components/LikelyLineupPanel";
import { SquadDepthPanel } from "../components/SquadDepthPanel";
import { TacticalProfilePanel } from "../components/TacticalProfilePanel";
import { countryNameJa } from "../data/countryNamesJa";
import type { PlayerSummary, TeamOut } from "../types/domain";

const DATA_CONFIDENCE_LABELS: Record<string, string> = {
  official: "公式",
  external: "外部データ",
  estimated: "推定",
  mixed: "混合(手動補正あり)",
  manual: "手動",
  missing: "データ欠落",
};

function confidenceLabel(value: string): string {
  return DATA_CONFIDENCE_LABELS[value] ?? value;
}

function summarizeTrust(players: PlayerSummary[]) {
  const byConfidence: Record<string, number> = {};
  let uncertaintySum = 0;
  let uncertaintyCount = 0;
  let lowConfidenceCount = 0;
  for (const p of players) {
    const key = p.data_confidence ?? "不明";
    byConfidence[key] = (byConfidence[key] ?? 0) + 1;
    if (p.uncertainty != null) {
      uncertaintySum += p.uncertainty;
      uncertaintyCount += 1;
    }
    if (p.low_confidence_attributes.length > 0) lowConfidenceCount += 1;
  }
  return {
    byConfidence,
    avgUncertainty: uncertaintyCount > 0 ? uncertaintySum / uncertaintyCount : null,
    lowConfidenceCount,
  };
}

function capsGoals(player: PlayerSummary): string {
  if (player.caps == null && player.national_team_goals == null) return "-";
  const caps = player.caps ?? 0;
  const goals = player.national_team_goals ?? 0;
  return `${caps}試合/${goals}得点`;
}

type PlayerSortMode = "overall" | "starter" | "caps" | "age";
type PositionFilter = "all" | "GK" | "DF" | "MF" | "FW";

function positionGroup(position: string): PositionFilter {
  const p = position.toUpperCase();
  if (p.includes("GK")) return "GK";
  if (p.includes("CB") || p.includes("LB") || p.includes("RB") || p.includes("DF")) return "DF";
  if (p.includes("DM") || p.includes("CM") || p.includes("AM") || p.includes("MF")) return "MF";
  return "FW";
}

function sortPlayers(players: PlayerSummary[], sortMode: PlayerSortMode): PlayerSummary[] {
  return [...players].sort((a, b) => {
    if (sortMode === "starter") return (b.starting_probability ?? -1) - (a.starting_probability ?? -1) || b.overall - a.overall;
    if (sortMode === "caps") return (b.caps ?? -1) - (a.caps ?? -1) || b.overall - a.overall;
    if (sortMode === "age") return b.age - a.age || b.overall - a.overall;
    return b.overall - a.overall;
  });
}

export function TeamPage() {
  const { teamId } = useParams<{ teamId: string }>();
  const [team, setTeam] = useState<TeamOut | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [playerQuery, setPlayerQuery] = useState("");
  const [positionFilter, setPositionFilter] = useState<PositionFilter>("all");
  const [playerSortMode, setPlayerSortMode] = useState<PlayerSortMode>("overall");

  useEffect(() => {
    if (!teamId) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- intentional reset of stale team data before refetching on teamId change
    setTeam(null);
    setError(null);
    api.getTeam(teamId).then(setTeam).catch((e) => setError(String(e)));
  }, [teamId]);

  const visiblePlayers = useMemo(() => {
    if (!team) return [];
    const q = playerQuery.trim().toLowerCase();
    const filtered = team.players.filter((p) => {
      if (positionFilter !== "all" && positionGroup(p.primary_position) !== positionFilter) return false;
      if (!q) return true;
      return (
        p.name.toLowerCase().includes(q) ||
        (p.name_ja?.toLowerCase().includes(q) ?? false) ||
        p.primary_position.toLowerCase().includes(q) ||
        (p.club_name?.toLowerCase().includes(q) ?? false)
      );
    });
    return sortPlayers(filtered, playerSortMode);
  }, [playerQuery, playerSortMode, positionFilter, team]);

  if (error) {
    return (
      <div className="space-y-3">
        <Link to="/simulate" className="text-sm text-slate-400 hover:text-slate-200">
          ← 試合シミュレーターに戻る
        </Link>
        <p className="text-rose-400">
          {error.includes("404") ? "指定されたチームが見つかりませんでした。" : "チームデータの読み込みに失敗しました。"}
        </p>
      </div>
    );
  }
  if (!team || !teamId) return <p className="text-slate-400">読み込み中...</p>;

  const trust = summarizeTrust(team.players);

  return (
    <div className="space-y-6">
      <div>
        <Link to="/simulate" className="text-sm text-slate-400 hover:text-slate-200">
          ← 試合シミュレーターに戻る
        </Link>
        <div className="mt-2 flex items-center gap-3">
          <span className="rounded bg-slate-700 px-2 py-1 text-sm font-bold text-slate-100">{team.id}</span>
          <h1 className="text-2xl font-bold">{countryNameJa(team.id, team.name)}</h1>
        </div>
        <p className="mt-1 text-sm text-slate-400">
          監督: {team.tactical_profile?.manager_name ?? "-"} / フォーメーション: {team.default_formation} / FIFAランク: {team.fifa_rank ?? "-"}
        </p>
      </div>

      <TacticalProfilePanel profile={team.tactical_profile} formation={team.default_formation} />

      <SquadDepthPanel players={team.players} />

      <div className="rounded-xl border border-slate-700 bg-slate-800/40 p-4">
        <p className="text-xs uppercase tracking-widest text-slate-500">データ信頼性</p>

        <div className="mt-3 flex flex-wrap items-center gap-4 text-xs text-slate-300">
          <span>
            選手数: <span className="font-semibold text-slate-100">{team.players.length}</span>
          </span>
          {Object.entries(trust.byConfidence).map(([key, count]) => (
            <span key={key}>
              {confidenceLabel(key)}: <span className="font-semibold text-slate-100">{count}</span>
            </span>
          ))}
          {trust.avgUncertainty != null && (
            <span>
              平均不確実性: <span className="font-semibold text-slate-100">{trust.avgUncertainty.toFixed(2)}</span>
            </span>
          )}
          {trust.lowConfidenceCount > 0 && (
            <span>
              低信頼度属性あり: <span className="font-semibold text-amber-400">{trust.lowConfidenceCount}人</span>
            </span>
          )}
        </div>

        <p className="mt-3 text-[11px] text-slate-500">
          スタメン予測・選手能力値はFIFAが公式発表したものではなく、公開データから推定したものです。クラブ・代表出場数などの公式プロフィール項目はFIFA Squad Listを基にしています。
        </p>
      </div>

      <div className="rounded-xl border border-slate-700 bg-slate-800/40 p-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-xs uppercase tracking-widest text-slate-500">選手一覧</p>
            <p className="mt-1 text-xs text-slate-500">
              表示中: {visiblePlayers.length}/{team.players.length}人
            </p>
          </div>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
            <label>
              <span className="text-[11px] text-slate-500">検索</span>
              <input
                value={playerQuery}
                onChange={(e) => setPlayerQuery(e.target.value)}
                placeholder="選手名・クラブ"
                className="mt-1 w-full rounded-md border border-slate-600 bg-slate-900 px-2 py-1.5 text-xs text-slate-100 outline-none placeholder:text-slate-600 focus:border-emerald-500"
              />
            </label>
            <label>
              <span className="text-[11px] text-slate-500">位置</span>
              <select
                value={positionFilter}
                onChange={(e) => setPositionFilter(e.target.value as PositionFilter)}
                className="mt-1 w-full rounded-md border border-slate-600 bg-slate-900 px-2 py-1.5 text-xs text-slate-100 outline-none focus:border-emerald-500"
              >
                <option value="all">全ポジション</option>
                <option value="GK">GK</option>
                <option value="DF">守備</option>
                <option value="MF">中盤</option>
                <option value="FW">攻撃</option>
              </select>
            </label>
            <label>
              <span className="text-[11px] text-slate-500">並び替え</span>
              <select
                value={playerSortMode}
                onChange={(e) => setPlayerSortMode(e.target.value as PlayerSortMode)}
                className="mt-1 w-full rounded-md border border-slate-600 bg-slate-900 px-2 py-1.5 text-xs text-slate-100 outline-none focus:border-emerald-500"
              >
                <option value="overall">能力値</option>
                <option value="starter">先発確率</option>
                <option value="caps">代表経験</option>
                <option value="age">年齢</option>
              </select>
            </label>
          </div>
        </div>
        <div className="mt-2 max-h-[420px] overflow-x-auto overflow-y-auto">
          <table className="min-w-[680px] w-full text-left text-xs">
            <thead className="sticky top-0 bg-slate-800/95 text-slate-500">
              <tr>
                <th className="py-1 pr-3 font-normal">選手名</th>
                <th className="py-1 pr-2 font-normal">位置</th>
                <th className="py-1 pr-2 text-right font-normal">能力値</th>
                <th className="py-1 pr-2 text-right font-normal">代表成績</th>
                <th className="py-1 pr-2 text-right font-normal">先発確率</th>
                <th className="py-1 text-right font-normal">信頼度</th>
              </tr>
            </thead>
            <tbody>
              {visiblePlayers.map((p) => (
                <tr key={p.id} className="border-t border-slate-700/60 text-slate-200">
                  <td className="py-1.5 pr-3">
                    <div className="font-medium">{p.name_ja ?? p.name}</div>
                    <div className="max-w-[14rem] truncate text-[10px] text-slate-500">{p.club_name ?? "クラブ未取得"}</div>
                  </td>
                  <td className="py-1.5 pr-2 text-slate-400">{p.primary_position}</td>
                  <td className="py-1.5 pr-2 text-right font-semibold">{p.overall}</td>
                  <td className="py-1.5 pr-2 text-right text-slate-300">{capsGoals(p)}</td>
                  <td className="py-1.5 pr-2 text-right text-slate-300">
                    {p.starting_probability != null ? `${Math.round(p.starting_probability)}%` : "-"}
                  </td>
                  <td className="py-1.5 text-right text-slate-400">
                    {p.data_confidence ? confidenceLabel(p.data_confidence) : "-"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {visiblePlayers.length === 0 && (
            <p className="py-6 text-center text-sm text-slate-500">条件に合う選手がいません。</p>
          )}
        </div>
      </div>

      <LikelyLineupPanel teamId={teamId} />
    </div>
  );
}
