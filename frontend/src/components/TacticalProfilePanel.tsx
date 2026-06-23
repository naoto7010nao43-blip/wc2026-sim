import type { TacticalProfile } from "../types/domain";

interface TacticalProfilePanelProps {
  profile: TacticalProfile | null;
  formation: string;
  compact?: boolean;
}

type AxisKey = "press_intensity" | "possession_style" | "defensive_line_height";

interface AxisView {
  key: AxisKey;
  label: string;
  lowLabel: string;
  highLabel: string;
  value: number;
  description: string;
}

function clampScore(value: number): number {
  return Math.max(0, Math.min(100, value));
}

function styleBand(value: number, low: string, balanced: string, high: string): string {
  if (value >= 70) return high;
  if (value <= 40) return low;
  return balanced;
}

function tacticalAxes(profile: TacticalProfile): AxisView[] {
  return [
    {
      key: "press_intensity",
      label: "プレス強度",
      lowLabel: "構える",
      highLabel: "奪いに行く",
      value: clampScore(profile.press_intensity),
      description: styleBand(profile.press_intensity, "低めのブロックを作りやすい", "状況に応じて前から行く", "高い位置で奪回を狙う"),
    },
    {
      key: "possession_style",
      label: "保持志向",
      lowLabel: "縦に速い",
      highLabel: "保持する",
      value: clampScore(profile.possession_style),
      description: styleBand(profile.possession_style, "早めに前進する", "保持と速攻を使い分ける", "ボール保持で試合を管理する"),
    },
    {
      key: "defensive_line_height",
      label: "最終ライン",
      lowLabel: "低め",
      highLabel: "高め",
      value: clampScore(profile.defensive_line_height),
      description: styleBand(profile.defensive_line_height, "背後のリスクを抑える", "標準的なライン設定", "陣地回復を優先する"),
    },
  ];
}

function tacticalSummary(profile: TacticalProfile): string {
  return [
    styleBand(profile.press_intensity, "ブロック重視", "標準プレス", "ハイプレス"),
    styleBand(profile.possession_style, "速攻寄り", "バランス保持", "保持志向"),
    styleBand(profile.defensive_line_height, "低めのライン", "標準ライン", "高いライン"),
  ].join(" / ");
}

function AxisMeter({ axis, compact }: { axis: AxisView; compact: boolean }) {
  return (
    <div className="rounded-lg border border-slate-700/80 bg-slate-900/45 p-3">
      <div className="flex items-center justify-between gap-3 text-xs">
        <span className="font-semibold text-slate-200">{axis.label}</span>
        <span className="text-slate-400">{axis.value}</span>
      </div>
      <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-700">
        <div className="h-full rounded-full bg-emerald-500" style={{ width: `${axis.value}%` }} />
      </div>
      <div className="mt-1 flex justify-between text-[10px] text-slate-500">
        <span>{axis.lowLabel}</span>
        <span>{axis.highLabel}</span>
      </div>
      {!compact && <p className="mt-2 text-[11px] leading-relaxed text-slate-400">{axis.description}</p>}
    </div>
  );
}

export function TacticalProfilePanel({ profile, formation, compact = false }: TacticalProfilePanelProps) {
  if (!profile) {
    return (
      <section className="rounded-xl border border-slate-700 bg-slate-800/40 p-4">
        <p className="text-xs uppercase tracking-widest text-slate-500">監督・戦術モデル</p>
        <p className="mt-2 text-sm text-slate-400">このチームの戦術プロファイルはまだ登録されていません。</p>
      </section>
    );
  }

  const axes = tacticalAxes(profile);

  return (
    <section className="rounded-xl border border-slate-700 bg-slate-800/40 p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-xs uppercase tracking-widest text-slate-500">監督・戦術モデル</p>
          <h2 className="mt-1 text-lg font-bold text-slate-100">{profile.manager_name}</h2>
          <p className="mt-1 text-sm text-slate-400">
            {formation} / {tacticalSummary(profile)}
          </p>
        </div>
        <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-xs text-emerald-200">
          予測モデル反映済み
        </div>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-3">
        {axes.map((axis) => (
          <AxisMeter key={axis.key} axis={axis} compact={compact} />
        ))}
      </div>

      {!compact && (
        <div className="mt-4 rounded-lg border border-slate-700/80 bg-slate-900/40 p-3">
          <p className="text-xs font-semibold text-slate-300">シミュレーション上の扱い</p>
          <ul className="mt-2 space-y-1 text-xs leading-relaxed text-slate-400">
            <li>・プレス強度は相手の保持志向・守備ラインとの噛み合わせで期待得点を微調整します。</li>
            <li>・保持志向とライン高さは、試合の支配傾向と背後のリスクを読むための補助指標です。</li>
            <li>・詳細シミュレーションでは点差や時間帯に応じて、監督判断として強度とラインが変化します。</li>
          </ul>
        </div>
      )}
    </section>
  );
}

