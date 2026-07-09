import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import { MatchPredictionPanel } from "../components/MatchPredictionPanel";
import { MatchupBreakdownPanel } from "../components/MatchupBreakdownPanel";
import { TacticalMatchupPanel } from "../components/TacticalMatchupPanel";
import { countryNameJa } from "../data/countryNamesJa";
import type { DataQualitySummary, TeamSummary } from "../types/domain";

export function SimulatorPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const queryHomeTeamId = searchParams.get("home")?.toUpperCase() ?? "";
  const queryAwayTeamId = searchParams.get("away")?.toUpperCase() ?? "";
  const querySeed = searchParams.get("seed") ?? "";
  const queryRun = searchParams.get("run") === "1";
  const queryDecisive = searchParams.get("decisive") === "1";
  const [teams, setTeams] = useState<TeamSummary[]>([]);
  const [homeTeamId, setHomeTeamId] = useState("");
  const [awayTeamId, setAwayTeamId] = useState("");
  const [dataQuality, setDataQuality] = useState<DataQualitySummary | null>(null);
  const [seed, setSeed] = useState(querySeed);
  const [decisive, setDecisive] = useState(queryDecisive);
  const [copied, setCopied] = useState(false);
  const autoRunRef = useRef(queryRun);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listTeams().then((data) => {
      const sorted = [...data].sort((a, b) => (a.group_id ?? "").localeCompare(b.group_id ?? "") || a.name.localeCompare(b.name));
      setTeams(sorted);
      if (sorted.length >= 2) {
        const teamIds = new Set(sorted.map((team) => team.id));
        const nextHome = teamIds.has(queryHomeTeamId) ? queryHomeTeamId : sorted[0].id;
        const fallbackAway = sorted.find((team) => team.id !== nextHome)?.id ?? sorted[1].id;
        const nextAway = teamIds.has(queryAwayTeamId) && queryAwayTeamId !== nextHome ? queryAwayTeamId : fallbackAway;
        setHomeTeamId(nextHome);
        setAwayTeamId(nextAway);
      }
    });
  }, [queryHomeTeamId, queryAwayTeamId]);

  useEffect(() => {
    let cancelled = false;
    api
      .getDataQualitySummary()
      .then((data) => {
        if (!cancelled) setDataQuality(data);
      })
      .catch(() => {
        if (!cancelled) setDataQuality(null);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const homeTeam = useMemo(() => teams.find((t) => t.id === homeTeamId), [teams, homeTeamId]);
  const awayTeam = useMemo(() => teams.find((t) => t.id === awayTeamId), [teams, awayTeamId]);
  const trimmedSeed = seed.trim();
  const parsedSeed = trimmedSeed === "" ? undefined : Number(trimmedSeed);
  const seedIsValid = trimmedSeed === "" || (typeof parsedSeed === "number" && Number.isInteger(parsedSeed));
  const sameTeamsSelected = Boolean(homeTeamId && awayTeamId && homeTeamId === awayTeamId);
  const canRunSimulation = teams.length > 0 && !loading && !sameTeamsSelected && seedIsValid;

  // 共有URL(run=1)からの自動実行: チームがURL通りに確定した後、一度だけ走らせる
  useEffect(() => {
    if (!autoRunRef.current) return;
    if (!homeTeamId || !awayTeamId || homeTeamId === awayTeamId) return;
    if (homeTeamId !== queryHomeTeamId || awayTeamId !== queryAwayTeamId) return;
    autoRunRef.current = false;
    const sharedSeed = querySeed.trim() === "" ? undefined : Number(querySeed);
    if (sharedSeed !== undefined && !Number.isInteger(sharedSeed)) return;
    api
      .simulateMatch(homeTeamId, awayTeamId, { seed: sharedSeed, allowDraw: !queryDecisive })
      .then((match) => {
        navigate(`/matches/${match.id}`);
      })
      .catch((e) => {
        setError(String(e));
        setLoading(false);
      });
    // 非同期チェーン内でのみ状態を更新する(eslint: set-state-in-effect 対応)
    queueMicrotask(() => setLoading(true));
  }, [homeTeamId, awayTeamId, queryHomeTeamId, queryAwayTeamId, querySeed, queryDecisive, navigate]);

  async function runSimulation() {
    if (!homeTeamId || !awayTeamId || homeTeamId === awayTeamId) {
      setError("異なる2チームを選択してください。");
      return;
    }
    if (!seedIsValid) {
      setError("シードは整数で入力してください。");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const match = await api.simulateMatch(homeTeamId, awayTeamId, {
        seed: parsedSeed,
        allowDraw: !decisive,
      });
      navigate(`/matches/${match.id}`);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  function shareUrl(): string {
    const params = new URLSearchParams({ home: homeTeamId, away: awayTeamId });
    if (trimmedSeed !== "") params.set("seed", trimmedSeed);
    if (decisive) params.set("decisive", "1");
    params.set("run", "1");
    return `${window.location.origin}/simulate?${params.toString()}`;
  }

  async function copyShareUrl() {
    try {
      await navigator.clipboard.writeText(shareUrl());
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      window.prompt("このURLをコピーしてください:", shareUrl());
    }
  }

  return (
    <div className="space-y-6">
      <section className="panel fade-up p-5 sm:p-6">
        <p className="font-display text-[11px] font-bold uppercase tracking-[0.3em] text-emerald-400">Match Simulator</p>
        <h2 className="mt-1 font-display text-2xl font-extrabold tracking-wide">試合シミュレーター</h2>
        <p className="mt-1 text-sm text-slate-400">
          気になる対戦カードを選んで、その1試合だけを詳細にシミュレーションします。
        </p>

        <div className="relative mt-5 grid grid-cols-1 gap-6 sm:grid-cols-2 sm:gap-10">
          <span aria-hidden className="score-num pointer-events-none absolute left-1/2 top-9 hidden -translate-x-1/2 text-xl text-slate-600 sm:block">VS</span>
          <div>
            <label className="block text-sm font-medium text-slate-300"><span className="mr-1.5 inline-block h-2 w-2 rounded-full bg-emerald-400 align-middle" />ホームチーム</label>
            <select
              value={homeTeamId}
              onChange={(e) => setHomeTeamId(e.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-slate-100 transition focus:border-emerald-500"
            >
              {teams.map((t) => (
                <option key={t.id} value={t.id}>
                  [{t.group_id}] {countryNameJa(t.id, t.name)} ({t.id})
                </option>
              ))}
            </select>
            <p className="mt-2 text-xs text-slate-500">
              監督: {homeTeam?.tactical_profile?.manager_name ?? "-"} / フォーメーション: {homeTeam?.default_formation ?? "-"}
            </p>
            {homeTeamId && (
              <Link to={`/teams/${homeTeamId}`} className="mt-1 inline-block text-xs text-emerald-400 hover:text-emerald-300">
                予測スタメンを見る →
              </Link>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300"><span className="mr-1.5 inline-block h-2 w-2 rounded-full bg-slate-500 align-middle" />アウェイチーム</label>
            <select
              value={awayTeamId}
              onChange={(e) => setAwayTeamId(e.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-slate-100 transition focus:border-emerald-500"
            >
              {teams.map((t) => (
                <option key={t.id} value={t.id}>
                  [{t.group_id}] {countryNameJa(t.id, t.name)} ({t.id})
                </option>
              ))}
            </select>
            <p className="mt-2 text-xs text-slate-500">
              監督: {awayTeam?.tactical_profile?.manager_name ?? "-"} / フォーメーション: {awayTeam?.default_formation ?? "-"}
            </p>
            {awayTeamId && (
              <Link to={`/teams/${awayTeamId}`} className="mt-1 inline-block text-xs text-emerald-400 hover:text-emerald-300">
                予測スタメンを見る →
              </Link>
            )}
          </div>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-4">
          <label className="flex items-center gap-2 text-sm text-slate-400">
            シード任意:
            <input
              value={seed}
              onChange={(e) => setSeed(e.target.value)}
              placeholder="ランダム"
              inputMode="numeric"
              className="w-28 rounded-md border border-slate-600 bg-slate-900 px-2 py-1 text-slate-100"
            />
          </label>
          <label className="flex items-center gap-2 text-sm text-slate-400">
            <input type="checkbox" checked={decisive} onChange={(e) => setDecisive(e.target.checked)} />
            引き分けなし（延長・PK）
          </label>
        </div>

        {(sameTeamsSelected || !seedIsValid) && (
          <p className="mt-3 text-xs text-amber-300">
            {sameTeamsSelected ? "同じチーム同士では実行できません。左右で異なる国を選んでください。" : "シードは空欄、または整数だけを指定できます。"}
          </p>
        )}

        {error && <p className="mt-3 text-sm text-rose-400">{error}</p>}

        <div className="mt-5 flex flex-wrap items-center gap-3">
          <button onClick={runSimulation} disabled={!canRunSimulation} className="btn-primary px-6 py-2.5">
            {loading ? "シミュレーション中..." : "シミュレーション開始"}
          </button>
          <button
            onClick={copyShareUrl}
            disabled={!homeTeamId || !awayTeamId || sameTeamsSelected}
            className="btn-secondary px-4 py-2.5 text-sm"
            title="この対戦条件(チーム・シード)を再現できるURLをコピーします"
          >
            {copied ? "コピーしました ✓" : "対戦リンクをコピー"}
          </button>
        </div>
        <p className="mt-2 text-[11px] text-slate-500">
          対戦リンクを開くと同じ条件で自動実行されます。シードを指定すると全く同じ試合展開を再現できます。
        </p>
      </section>

      <TacticalMatchupPanel homeTeam={homeTeam} awayTeam={awayTeam} />

      {homeTeamId && awayTeamId && homeTeamId !== awayTeamId && (
        <MatchupBreakdownPanel homeTeamId={homeTeamId} awayTeamId={awayTeamId} />
      )}

      {homeTeamId && awayTeamId && homeTeamId !== awayTeamId && (
        <MatchPredictionPanel homeTeamId={homeTeamId} awayTeamId={awayTeamId} dataQuality={dataQuality} />
      )}
    </div>
  );
}
