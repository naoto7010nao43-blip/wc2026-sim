import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import { TeamBadge } from "../components/TeamBadge";
import type { MatchPredictionOut, MatchSummary, TournamentResult } from "../types/domain";

type Outcome = "home" | "draw" | "away";

interface EvaluatedMatch {
  match: MatchSummary;
  prediction: MatchPredictionOut;
  predicted: Outcome;
  actual: Outcome;
  hit: boolean;
  probOfActual: number;
  exactScoreHit: boolean;
}

function actualOutcome(m: MatchSummary): Outcome {
  // PK戦にもつれた試合は、90分(+延長)時点では引き分け扱いとする
  if (m.went_to_penalties) return "draw";
  if (m.home_score > m.away_score) return "home";
  if (m.home_score < m.away_score) return "away";
  return "draw";
}

function predictedOutcome(p: MatchPredictionOut): Outcome {
  if (p.home_win_pct >= p.draw_pct && p.home_win_pct >= p.away_win_pct) return "home";
  if (p.away_win_pct >= p.home_win_pct && p.away_win_pct >= p.draw_pct) return "away";
  return "draw";
}

function probOf(p: MatchPredictionOut, o: Outcome): number {
  return o === "home" ? p.home_win_pct : o === "away" ? p.away_win_pct : p.draw_pct;
}

const OUTCOME_LABEL: Record<Outcome, string> = { home: "ホーム勝ち", draw: "引き分け", away: "アウェイ勝ち" };

/** 同時実行数を絞って全実試合の予測を取得する */
async function evaluateAll(
  matches: MatchSummary[],
  onProgress: (done: number) => void,
): Promise<EvaluatedMatch[]> {
  const results: EvaluatedMatch[] = [];
  let done = 0;
  const queue = [...matches];
  const CONCURRENCY = 4;

  async function worker() {
    for (;;) {
      const m = queue.shift();
      if (!m) return;
      try {
        const prediction = await api.getMatchPrediction(m.home_team_id, m.away_team_id);
        const predicted = predictedOutcome(prediction);
        const actual = actualOutcome(m);
        const top = prediction.most_likely_scores[0];
        const exactScoreHit =
          !m.went_to_penalties && top != null && top[0] === m.home_score && top[1] === m.away_score;
        results.push({
          match: m,
          prediction,
          predicted,
          actual,
          hit: predicted === actual,
          probOfActual: probOf(prediction, actual),
          exactScoreHit,
        });
      } catch {
        // 個別の失敗はスキップ(レート制限等)。全体の集計から除外する。
      } finally {
        done += 1;
        onProgress(done);
      }
    }
  }

  await Promise.all(Array.from({ length: CONCURRENCY }, () => worker()));
  results.sort((a, b) => a.match.played_at.localeCompare(b.match.played_at));
  return results;
}

export function AccuracyPage() {
  const [state, setState] = useState<TournamentResult | null>(null);
  const [restoring, setRestoring] = useState(true);
  const [evaluated, setEvaluated] = useState<EvaluatedMatch[] | null>(null);
  const [progress, setProgress] = useState(0);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showMisses, setShowMisses] = useState(false);

  useEffect(() => {
    api
      .getTournamentState()
      .then(setState)
      .catch((e) => setError(String(e)))
      .finally(() => setRestoring(false));
  }, []);

  const realMatches = useMemo(() => {
    if (!state) return [];
    const all: MatchSummary[] = [
      ...(state.matches.group ?? []),
      ...(state.matches.R32 ?? []),
      ...(state.matches.R16 ?? []),
      ...(state.matches.QF ?? []),
      ...(state.matches.SF ?? []),
      ...(state.matches.THIRD_PLACE ?? []),
      ...(state.matches.FINAL ?? []),
    ];
    return all.filter((m) => m.is_real && m.status === "completed");
  }, [state]);

  async function run() {
    setRunning(true);
    setError(null);
    setProgress(0);
    try {
      const results = await evaluateAll(realMatches, setProgress);
      setEvaluated(results);
    } catch (e) {
      setError(String(e));
    } finally {
      setRunning(false);
    }
  }

  const summary = useMemo(() => {
    if (!evaluated || evaluated.length === 0) return null;
    const n = evaluated.length;
    const hits = evaluated.filter((e) => e.hit).length;
    const exact = evaluated.filter((e) => e.exactScoreHit).length;
    const avgProb = evaluated.reduce((s, e) => s + e.probOfActual, 0) / n;
    return { n, hits, hitRate: (100 * hits) / n, exact, exactRate: (100 * exact) / n, avgProb };
  }, [evaluated]);

  const visibleRows = useMemo(() => {
    if (!evaluated) return [];
    return showMisses ? evaluated.filter((e) => !e.hit) : evaluated;
  }, [evaluated, showMisses]);

  return (
    <div className="space-y-5">
      <section className="panel fade-up p-5 sm:p-6">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="font-display text-[11px] font-bold uppercase tracking-[0.3em] text-emerald-400">Model Accuracy</p>
            <h2 className="mt-1 font-display text-2xl font-extrabold tracking-wide">的中実績</h2>
            <p className="mt-1 max-w-xl text-sm text-slate-400">
              実際に行われた全{realMatches.length}試合に対して、現在の予測モデルの「答え合わせ」を行います。
              各試合の勝敗予測(最も確率が高い結果)と実際の結果を突き合わせます。
            </p>
          </div>
          <button onClick={run} disabled={running || restoring || realMatches.length === 0} className="btn-primary px-6 py-2.5">
            {running ? `検証中... ${progress}/${realMatches.length}` : evaluated ? "再検証する" : "答え合わせを実行"}
          </button>
        </div>
        {running && (
          <div className="mt-4 h-2 overflow-hidden rounded-full bg-slate-800">
            <div
              className="h-full rounded-full bg-gradient-to-r from-emerald-600 to-emerald-400 transition-[width] duration-300"
              style={{ width: `${realMatches.length > 0 ? (100 * progress) / realMatches.length : 0}%` }}
            />
          </div>
        )}
        {error && <p className="mt-3 text-sm text-rose-400">{error}</p>}
        {!restoring && realMatches.length === 0 && (
          <p className="mt-3 text-sm text-slate-400">
            実結果データが見つかりません。大会モードで一度シミュレーションを実行すると実結果が読み込まれます。
          </p>
        )}
      </section>

      {summary && (
        <>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <BigMetric label="勝敗の的中率" value={`${summary.hitRate.toFixed(1)}%`} sub={`${summary.hits} / ${summary.n}試合`} accent />
            <BigMetric label="スコア完全一致" value={`${summary.exactRate.toFixed(1)}%`} sub={`${summary.exact} / ${summary.n}試合`} />
            <BigMetric label="実際の結果に置いた確率(平均)" value={`${summary.avgProb.toFixed(1)}%`} sub="高いほど自信と結果が一致" />
            <BigMetric label="検証対象" value={`${summary.n}試合`} sub="実結果のみ" />
          </div>

          <p className="text-[11px] leading-relaxed text-slate-500">
            ※ 3択(勝ち/分け/負け)のランダム予測は約33%です。PK戦にもつれた試合は90分時点の引き分けとして判定しています。
            予測は現在のモデル・データによる事後計算のため、試合当時の予測とは異なる場合があります。
          </p>

          <div className="flex items-center justify-between gap-3">
            <h3 className="flex items-center gap-2 font-display text-xl font-extrabold tracking-wide">
              <span className="h-5 w-1 rounded-full bg-emerald-400" />
              試合ごとの検証結果
            </h3>
            <label className="flex cursor-pointer items-center gap-2 text-xs text-slate-400">
              <input type="checkbox" checked={showMisses} onChange={(e) => setShowMisses(e.target.checked)} />
              外した試合のみ表示
            </label>
          </div>

          <div className="space-y-2">
            {visibleRows.map((e) => (
              <EvaluatedRow key={e.match.id} row={e} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function BigMetric({ label, value, sub, accent = false }: { label: string; value: string; sub: string; accent?: boolean }) {
  return (
    <div className={`panel p-4 ${accent ? "border-emerald-500/50" : ""}`}>
      <p className="text-[11px] text-slate-500">{label}</p>
      <p className={`score-num mt-1 text-3xl ${accent ? "text-emerald-300" : "text-slate-100"}`}>{value}</p>
      <p className="mt-1 text-[11px] text-slate-500">{sub}</p>
    </div>
  );
}

function EvaluatedRow({ row }: { row: EvaluatedMatch }) {
  const { match: m, prediction: p } = row;
  return (
    <div className={`panel p-3 ${row.hit ? "" : "border-rose-500/30"}`}>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <span
          className={`score-num flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-sm ${
            row.hit ? "bg-emerald-500/20 text-emerald-300" : "bg-rose-500/15 text-rose-300"
          }`}
          title={row.hit ? "勝敗予測が的中" : "勝敗予測が外れ"}
        >
          {row.hit ? "○" : "×"}
        </span>
        <div className="flex min-w-0 flex-1 items-center gap-2 text-sm">
          <TeamBadge teamId={m.home_team_id} />
          <span className="score-num shrink-0 rounded bg-slate-900/70 px-2 py-0.5 text-base text-slate-100">
            {m.home_score}–{m.away_score}
          </span>
          <TeamBadge teamId={m.away_team_id} />
          {m.went_to_penalties && <span className="shrink-0 text-[10px] text-amber-300">PK</span>}
        </div>
        <div className="text-right text-xs">
          <p className="text-slate-500">
            予測: <span className={row.hit ? "text-emerald-300" : "text-rose-300"}>{OUTCOME_LABEL[row.predicted]}</span>
            <span className="score-num ml-1 text-slate-400">({probOf(p, row.predicted).toFixed(0)}%)</span>
          </p>
          {row.exactScoreHit && <p className="mt-0.5 font-semibold text-amber-300">スコアも完全一致</p>}
        </div>
      </div>
      {/* 3択確率バー */}
      <div className="mt-2 flex h-1.5 overflow-hidden rounded-full">
        <div
          className={row.actual === "home" ? "bg-emerald-400" : "bg-slate-600"}
          style={{ width: `${p.home_win_pct}%` }}
          title={`ホーム勝ち ${p.home_win_pct.toFixed(1)}%`}
        />
        <div
          className={row.actual === "draw" ? "bg-emerald-400" : "bg-slate-700"}
          style={{ width: `${p.draw_pct}%` }}
          title={`引き分け ${p.draw_pct.toFixed(1)}%`}
        />
        <div
          className={row.actual === "away" ? "bg-emerald-400" : "bg-slate-800"}
          style={{ width: `${p.away_win_pct}%` }}
          title={`アウェイ勝ち ${p.away_win_pct.toFixed(1)}%`}
        />
      </div>
      <p className="mt-1 text-[10px] text-slate-600">
        バーの明るい部分 = 実際に起きた結果にモデルが置いていた確率({row.probOfActual.toFixed(1)}%)
      </p>
    </div>
  );
}
