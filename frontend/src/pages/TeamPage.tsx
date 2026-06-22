import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import { LikelyLineupPanel } from "../components/LikelyLineupPanel";
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

export function TeamPage() {
  const { teamId } = useParams<{ teamId: string }>();
  const [team, setTeam] = useState<TeamOut | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!teamId) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- intentional reset of stale team data before refetching on teamId change
    setTeam(null);
    setError(null);
    api.getTeam(teamId).then(setTeam).catch((e) => setError(String(e)));
  }, [teamId]);

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
  const sortedPlayers = [...team.players].sort((a, b) => b.overall - a.overall);

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

      <div className="rounded-xl border border-slate-700 bg-slate-800/40 p-4">
        <p className="text-xs uppercase tracking-widest text-slate-500">データ信頼性</p>

        {team.tactical_profile && (
          <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-3">
            {([
              ["プレス強度", team.tactical_profile.press_intensity],
              ["ポゼッション志向", team.tactical_profile.possession_style],
              ["最終ライン高さ", team.tactical_profile.defensive_line_height],
            ] as const).map(([label, value]) => (
              <div key={label}>
                <div className="flex items-center justify-between text-[11px] text-slate-400">
                  <span>{label}</span>
                  <span className="font-semibold text-slate-200">{value}</span>
                </div>
                <div className="mt-0.5 h-1 overflow-hidden rounded-full bg-slate-700">
                  <div className="h-full bg-emerald-500" style={{ width: `${value}%` }} />
                </div>
              </div>
            ))}
          </div>
        )}

        <div className="mt-4 flex flex-wrap items-center gap-4 text-xs text-slate-300">
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
          スタメン予測・選手能力値はFIFAが公式発表したものではなく、公開データから推定したものです。
        </p>
      </div>

      <div className="rounded-xl border border-slate-700 bg-slate-800/40 p-4">
        <p className="text-xs uppercase tracking-widest text-slate-500">選手一覧</p>
        <div className="mt-2 max-h-[420px] overflow-y-auto">
          <table className="w-full text-left text-xs">
            <thead className="sticky top-0 bg-slate-800/95 text-slate-500">
              <tr>
                <th className="py-1 pr-2 font-normal">選手名</th>
                <th className="py-1 pr-2 font-normal">位置</th>
                <th className="py-1 pr-2 text-right font-normal">能力値</th>
                <th className="py-1 pr-2 text-right font-normal">先発確率</th>
                <th className="py-1 text-right font-normal">信頼度</th>
              </tr>
            </thead>
            <tbody>
              {sortedPlayers.map((p) => (
                <tr key={p.id} className="border-t border-slate-700/60 text-slate-200">
                  <td className="py-1 pr-2">{p.name_ja ?? p.name}</td>
                  <td className="py-1 pr-2 text-slate-400">{p.primary_position}</td>
                  <td className="py-1 pr-2 text-right font-semibold">{p.overall}</td>
                  <td className="py-1 pr-2 text-right text-slate-300">
                    {p.starting_probability != null ? `${Math.round(p.starting_probability)}%` : "-"}
                  </td>
                  <td className="py-1 text-right text-slate-400">
                    {p.data_confidence ? confidenceLabel(p.data_confidence) : "-"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <LikelyLineupPanel teamId={teamId} />
    </div>
  );
}
