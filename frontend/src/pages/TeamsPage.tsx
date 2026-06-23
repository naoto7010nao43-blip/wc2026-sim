import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { countryNameJa } from "../data/countryNamesJa";
import type { TeamSummary } from "../types/domain";

const CONFEDERATION_ORDER = ["UEFA", "CONMEBOL", "CONCACAF", "CAF", "AFC", "OFC"];

function sortTeams(a: TeamSummary, b: TeamSummary): number {
  return (
    (a.group_id ?? "").localeCompare(b.group_id ?? "") ||
    (a.fifa_rank ?? 999) - (b.fifa_rank ?? 999) ||
    a.name.localeCompare(b.name)
  );
}

function groupedByConfederation(teams: TeamSummary[]): [string, TeamSummary[]][] {
  const grouped = teams.reduce<Record<string, TeamSummary[]>>((acc, team) => {
    (acc[team.confederation] ??= []).push(team);
    return acc;
  }, {});
  return Object.entries(grouped).sort((a, b) => {
    const ai = CONFEDERATION_ORDER.indexOf(a[0]);
    const bi = CONFEDERATION_ORDER.indexOf(b[0]);
    return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi) || a[0].localeCompare(b[0]);
  });
}

export function TeamsPage() {
  const [teams, setTeams] = useState<TeamSummary[]>([]);
  const [query, setQuery] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .listTeams()
      .then((data) => setTeams([...data].sort(sortTeams)))
      .catch((e) => setError(String(e)));
  }, []);

  const filteredTeams = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return teams;
    return teams.filter((team) => {
      const ja = countryNameJa(team.id, team.name).toLowerCase();
      return (
        team.id.toLowerCase().includes(q) ||
        team.name.toLowerCase().includes(q) ||
        ja.includes(q) ||
        (team.tactical_profile?.manager_name.toLowerCase().includes(q) ?? false)
      );
    });
  }, [query, teams]);

  const confederations = groupedByConfederation(filteredTeams);

  return (
    <div className="space-y-6">
      <section className="rounded-lg border border-slate-700 bg-slate-800/40 p-5">
        <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <h2 className="text-xl font-bold">チーム一覧</h2>
            <p className="mt-1 text-sm text-slate-400">
              出場48チームの監督、フォーメーション、FIFAランク、グループを確認できます。
            </p>
          </div>
          <label className="w-full md:max-w-xs">
            <span className="text-xs font-medium text-slate-400">検索</span>
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="国名・コード・監督名"
              className="mt-1 w-full rounded-md border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-slate-100 outline-none transition placeholder:text-slate-600 focus:border-emerald-500"
            />
          </label>
        </div>
        {error && <p className="mt-3 text-sm text-rose-400">チーム一覧の読み込みに失敗しました。</p>}
      </section>

      {teams.length === 0 && !error && <p className="text-sm text-slate-400">読み込み中...</p>}

      {teams.length > 0 && filteredTeams.length === 0 && (
        <p className="rounded-lg border border-slate-700 bg-slate-800/40 p-4 text-sm text-slate-400">
          条件に合うチームがありません。
        </p>
      )}

      {confederations.map(([confederation, rows]) => (
        <section key={confederation}>
          <div className="mb-3 flex items-center justify-between gap-3">
            <h3 className="text-sm font-bold tracking-wide text-emerald-400">{confederation}</h3>
            <span className="text-xs text-slate-500">{rows.length}チーム</span>
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {rows.map((team) => (
              <Link
                key={team.id}
                to={`/teams/${team.id}`}
                className="group rounded-lg border border-slate-700 bg-slate-800/55 p-4 transition hover:border-emerald-500 hover:bg-slate-800"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="rounded bg-slate-700 px-1.5 py-0.5 text-xs font-bold text-slate-100">{team.id}</span>
                      <h4 className="truncate text-sm font-bold text-slate-100 group-hover:text-emerald-300">
                        {countryNameJa(team.id, team.name)}
                      </h4>
                    </div>
                    <p className="mt-2 truncate text-xs text-slate-400">監督: {team.tactical_profile?.manager_name ?? "-"}</p>
                    <p className="mt-1 text-xs text-slate-500">フォーメーション: {team.default_formation}</p>
                  </div>
                  <div className="shrink-0 text-right text-xs">
                    <p className="text-slate-500">Group</p>
                    <p className="text-base font-bold text-slate-100">{team.group_id ?? "-"}</p>
                  </div>
                </div>
                <div className="mt-3 flex flex-wrap gap-2 text-[11px] text-slate-400">
                  <span className="rounded bg-slate-900/70 px-2 py-1">FIFA {team.fifa_rank ?? "-"}</span>
                  <span className="rounded bg-slate-900/70 px-2 py-1">{team.confederation}</span>
                </div>
              </Link>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
