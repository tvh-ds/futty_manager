import hashlib

import numpy as np
from sklearn.metrics import ndcg_score

from scout.contracts import RecruitmentBrief, Role


def brief_suite(engine):
    result = []
    for role in Role:
        peers = [player for player in engine.players.values() if role in player.roles]
        for index in range(6):
            brief = RecruitmentBrief(role=role, limit=20)
            if index == 1:
                brief.constraints.foot = "left"
            if index == 2:
                brief.constraints.max_age = 24
            if index == 3 and peers:
                brief.replacement_id = peers[0].id
            if index == 4:
                brief.constraints.attributes = ["high_line"]
            if index == 5:
                brief.weights = {"quality": 2, "coverage": 1}
            result.append({"id": f"{role.name}-{index + 1}", "split": "development" if index < 2 else "test",
                           "brief": brief.model_dump(mode="json"), "judgments": {}})
    return result


def evaluate(engine, cases: list[dict]):
    output = []
    for case in cases:
        brief = RecruitmentBrief.model_validate(case["brief"])
        ranked = engine.recommend(brief)
        ids = [item.player.id for item in ranked]
        variation = brief.model_copy(deep=True)
        variation.weights = {key: weight * (1.1 if key == "quality" else 0.95) for key, weight in brief.weights.items()}
        varied = [item.player.id for item in engine.recommend(variation)]
        union = set(ids[:10]) | set(varied[:10])
        stability = len(set(ids[:10]) & set(varied[:10])) / len(union) if union else 1.0
        judgments = case.get("judgments", {})
        relevance = [judgments.get(identity) for identity in ids]
        ndcg = None
        if len(relevance) > 1 and all(value is not None for value in relevance) and any(relevance):
            ndcg = float(ndcg_score([relevance], [list(range(len(ids), 0, -1))], k=10))
        output.append({"id": case["id"], "split": case["split"], "role": brief.role.value,
                       "returned": len(ids), "stability_jaccard_at_10": stability, "ndcg_at_10": ndcg,
                       "verification_required": sum(item.status == "verification_required" for item in ranked),
                       "ranking_sha256": hashlib.sha256("|".join(ids).encode()).hexdigest()})
    return {"release_id": engine.release.id, "data_kind": engine.release.kind, "cases": output,
            "mean_weight_stability": float(np.mean([case["stability_jaccard_at_10"] for case in output])),
            "judgment_status": "Personal judgments required; relevance is not certified by fixture tests",
            "limitations": ["Weight perturbation measures local sensitivity, not football validity",
                            "No human relevance metric is reported without supplied judgments"]}
