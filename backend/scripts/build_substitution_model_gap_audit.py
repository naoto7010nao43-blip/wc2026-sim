"""Build a read-only audit of the current substitution model gap.

The match engine can already make substitutions, but it uses one generic
fatigue/bench-quality rule for every manager and team. This report does not
change that behavior. It records what is currently modeled, what real-world
substitution research could inform later, and what should remain out of seed
data until a Codex-reviewed feature spec exists.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.engine.management import MAX_SUBS, SUB_CHANCE_PER_MINUTE, SUB_FATIGUE_GAP, SUB_WINDOW  # noqa: E402

REPORTS_DIR = BACKEND_DIR / "reports"


def build_engine_capabilities() -> dict[str, Any]:
    return {
        "hasSubstitutionEvents": True,
        "hasManagerSpecificSubstitutionParameters": False,
        "hasScoreStateSubstitutionBias": False,
        "hasPositionSpecificSubstitutionPreferences": False,
        "maxSubs": MAX_SUBS,
        "subWindow": {"startMinute": SUB_WINDOW[0], "endMinute": SUB_WINDOW[1]},
        "subChancePerMinute": SUB_CHANCE_PER_MINUTE,
        "subFatigueGap": SUB_FATIGUE_GAP,
        "selectionRule": "most_fatigued_matching_position_best_overall_bench",
    }


def build_gap_rows() -> list[dict[str, Any]]:
    return [
        {
            "gapId": "manager_specific_timing",
            "label": "監督別の交代タイミング",
            "currentBehavior": "全チームが55分から88分の同じ時間帯と同じ確率で交代を検討します。",
            "precisionRiskJa": "早めに動く監督、終盤まで引っ張る監督、延長を見据える監督の差が試合展開に出ません。",
            "futureFieldCandidates": ["substitution_aggressiveness", "first_sub_minute_bias", "late_substitution_patience"],
            "evidenceNeededJa": "直近公式戦の交代分布、リード時とビハインド時の初回交代分、主要大会での交代傾向。",
            "recommendedNextAction": "Claude Codeの外部調査では、数値を直接反映せず候補フィールド別に証拠を集める。",
        },
        {
            "gapId": "score_state_intent",
            "label": "スコア状況別の交代意図",
            "currentBehavior": "交代判断は疲労差が中心で、リード時の守備固めやビハインド時の攻撃的交代は区別しません。",
            "precisionRiskJa": "終盤の逃げ切り、同点狙い、勝ち越し狙いの監督判断が均質になり、観るシミュレーションとしての説得力が落ちます。",
            "futureFieldCandidates": ["protect_lead_sub_bias", "chasing_goal_sub_bias", "draw_state_risk_tolerance"],
            "evidenceNeededJa": "リード時・同点時・ビハインド時の交代ポジション、交代後のフォーメーション変化、守備/攻撃カード投入の頻度。",
            "recommendedNextAction": "まず候補レポートに留め、実装時は試合結果分布への影響をbefore/afterで検証する。",
        },
        {
            "gapId": "role_and_position_preference",
            "label": "ポジション・役割別の交代嗜好",
            "currentBehavior": "疲労した選手と近いポジションのベンチ選手からoverallが最も高い選手を選びます。",
            "precisionRiskJa": "サイドの入れ替え、CF投入、アンカー温存、カードをもらったDFの早期交代などの傾向が表現されません。",
            "futureFieldCandidates": ["wing_rotation_bias", "striker_chase_bias", "defensive_midfield_protection_bias", "card_risk_sub_bias"],
            "evidenceNeededJa": "交代で入る選手のポジション、交代で下げるポジション、カード保持者や負傷明け選手への対応。",
            "recommendedNextAction": "選手個人ではなく監督/チーム傾向として集め、個別試合のうわさを直接採用しない。",
        },
        {
            "gapId": "bench_trust_and_depth",
            "label": "控え選手への信頼度",
            "currentBehavior": "ベンチ選手のoverallだけで交代候補を選び、監督が信頼する控えや大会で使われやすい控えを区別しません。",
            "precisionRiskJa": "実際は重用される控え、守備固め要員、延長向けのPK要員などがいるため、試合終盤の人選が単調になります。",
            "futureFieldCandidates": ["bench_trust", "closer_role_players", "penalty_sub_preference"],
            "evidenceNeededJa": "直近の代表戦での交代出場回数、主要大会での投入順、PK戦を見据えた交代実績。",
            "recommendedNextAction": "選手能力値とは分離し、起用確率/監督傾向の補助データとして扱う。",
        },
    ]


def build_report() -> dict[str, Any]:
    generated_at = datetime.now(timezone.utc).isoformat()
    gaps = build_gap_rows()
    return {
        "generatedAt": generated_at,
        "sourceReports": [
            {"name": "app.engine.management", "generatedAt": generated_at},
            {"name": "docs/codex/EXTERNAL_DATA_VERIFICATION_CANDIDATES_2026-06-24", "generatedAt": None},
        ],
        "note": (
            "現在の交代ロジックは全チーム共通の疲労ベースです。この監査は、外部調査で集める選手交代データを"
            "どの将来フィールドへ整理すべきかを示す読み取り専用の設計メモです。試合ロジック、能力値、seedデータは変更しません。"
        ),
        "engineCapabilities": build_engine_capabilities(),
        "gapCount": len(gaps),
        "gaps": gaps,
        "recommendationsJa": [
            "選手交代の実データは、今すぐseed値へ反映せず、監督別の候補レポートとして蓄積してください。",
            "実装する場合は、交代タイミング、スコア状況、ポジション嗜好、控え信頼度を能力値とは別の入力として扱ってください。",
            "将来の実装前には、試合結果分布とイベントの説得力が改善するかをbefore/afterで検証してください。",
        ],
        "summary": {
            "currentModelHasManagerSpecificSubstitutions": False,
            "dataResearchCanBeStored": True,
            "safeCurrentAction": "read_only_candidate_collection",
            "recommendedNextSpec": "manager_substitution_tendency_model",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.parse_args()

    report = build_report()
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_path = REPORTS_DIR / f"substitution_model_gap_audit_{date_str}.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {out_path}")
    print(f"gapCount={report['gapCount']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
