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
from app.engine.state import NEUTRAL_SUBSTITUTION_PROFILE  # noqa: E402

REPORTS_DIR = BACKEND_DIR / "reports"


def build_engine_capabilities() -> dict[str, Any]:
    return {
        "hasSubstitutionEvents": True,
        # Spec 018 Phase 5 added the substitution_profile mechanism to
        # TeamState/maybe_substitute -- these are now True at the engine
        # level. anyTeamUsesNonNeutralProfile stays False because no team
        # has been given real, source-backed values yet; every team still
        # runs on NEUTRAL_SUBSTITUTION_PROFILE, which reproduces the
        # original fatigue-only behavior exactly.
        "hasManagerSpecificSubstitutionParameters": True,
        "hasScoreStateSubstitutionBias": True,
        "hasPositionSpecificSubstitutionPreferences": True,
        "anyTeamUsesNonNeutralProfile": False,
        "neutralSubstitutionProfileFields": sorted(NEUTRAL_SUBSTITUTION_PROFILE.keys()),
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
            "currentBehavior": (
                "Spec 018 Phase 5でfirst_sub_minute_biasという交代プロファイル項目を追加しましたが、"
                "現在は全チームが中立値(0分)のままで、実質的に全チーム55分から88分の同じ時間帯で交代を検討します。"
            ),
            "precisionRiskJa": "早めに動く監督、終盤まで引っ張る監督、延長を見据える監督の差が試合展開に出ません。",
            "futureFieldCandidates": ["substitution_aggressiveness", "first_sub_minute_bias", "late_substitution_patience"],
            "evidenceNeededJa": "直近公式戦の交代分布、リード時とビハインド時の初回交代分、主要大会での交代傾向。",
            "recommendedNextAction": "外部調査の候補レポートから、出典付きで値を確定できたチームのみ順次プロファイルへ反映する。",
        },
        {
            "gapId": "score_state_intent",
            "label": "スコア状況別の交代意図",
            "currentBehavior": (
                "Spec 018 Phase 5でtrailing_aggression/leading_defensive_biasという項目を追加し、"
                "スコア状況に応じて交代確率を変える仕組み自体は実装済みですが、現在は全チームが中立値のままで、"
                "リード時の守備固めやビハインド時の攻撃的交代は実質的に区別されません。"
            ),
            "precisionRiskJa": "終盤の逃げ切り、同点狙い、勝ち越し狙いの監督判断が均質になり、観るシミュレーションとしての説得力が落ちます。",
            "futureFieldCandidates": ["protect_lead_sub_bias", "chasing_goal_sub_bias", "draw_state_risk_tolerance"],
            "evidenceNeededJa": "リード時・同点時・ビハインド時の交代ポジション、交代後のフォーメーション変化、守備/攻撃カード投入の頻度。",
            "recommendedNextAction": "まず候補レポートに留め、実装時は試合結果分布への影響をbefore/afterで検証する。",
        },
        {
            "gapId": "role_and_position_preference",
            "label": "ポジション・役割別の交代嗜好",
            "currentBehavior": (
                "Spec 018 Phase 5でlike_for_like_preferenceという項目を追加し、同ポジション以外からの交代も"
                "選べる仕組み自体は実装済みですが、現在は全チームが中立値(常に同ポジション優先)のままです。"
            ),
            "precisionRiskJa": "サイドの入れ替え、CF投入、アンカー温存、カードをもらったDFの早期交代などの傾向が表現されません。",
            "futureFieldCandidates": ["wing_rotation_bias", "striker_chase_bias", "defensive_midfield_protection_bias", "card_risk_sub_bias"],
            "evidenceNeededJa": "交代で入る選手のポジション、交代で下げるポジション、カード保持者や負傷明け選手への対応。",
            "recommendedNextAction": "選手個人ではなく監督/チーム傾向として集め、個別試合のうわさを直接採用しない。",
        },
        {
            "gapId": "bench_trust_and_depth",
            "label": "控え選手への信頼度",
            "currentBehavior": (
                "Spec 018 Phase 5でbench_trustという項目を追加し、交代確率全体を上下させる仕組み自体は実装済みですが、"
                "現在は全チームが中立値のままで、控え選手の起用しやすさはoverallのみで決まります。"
            ),
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
            "Spec 018 Phase 5で交代プロファイルの仕組み自体(タイミング・スコア状況・ポジション嗜好・控え信頼度)は"
            "エンジンに実装済みですが、全チームが中立値のままで実質的な差はまだありません。この監査は、外部調査で集める"
            "選手交代データをどのチームのプロファイルへ反映すべきかを示す読み取り専用の設計メモです。"
            "試合ロジック自体、能力値、seedデータは変更しません。"
        ),
        "engineCapabilities": build_engine_capabilities(),
        "gapCount": len(gaps),
        "gaps": gaps,
        "recommendationsJa": [
            "選手交代の実データは、今すぐ全チームへ反映せず、出典付きで確定できたチームから順に候補レポートを経て反映してください。",
            "反映する場合は、交代タイミング、スコア状況、ポジション嗜好、控え信頼度を能力値とは別の入力として扱ってください。",
            "反映前には、試合結果分布とイベントの説得力が改善するかをbefore/afterで検証してください。",
        ],
        "summary": {
            "currentModelHasManagerSpecificSubstitutions": False,
            "substitutionProfileMechanismImplemented": True,
            "dataResearchCanBeStored": True,
            "safeCurrentAction": "read_only_candidate_collection",
            "recommendedNextSpec": "populate_real_per_team_substitution_profiles",
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
