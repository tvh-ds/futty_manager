import re

import httpx
from pydantic import ValidationError

from scout.contracts import RecruitmentBrief, Role
from scout.roles import ROLE_SPECS


def structured_suggestions(text: str):
    brief = RecruitmentBrief()
    lower = text.lower()
    aliases = [(Role.GK, r"goalkeeper|\bkeeper\b|\bgk\b"), (Role.FB, r"full.?back|wing.?back|\bfb\b"),
               (Role.CB, r"centre.?back|center.?back|\bcb\b"), (Role.DM, r"defensive midfielder|\bdm\b"),
               (Role.AM, r"attacking midfielder|\bam\b"), (Role.CM, r"central midfielder|\bcm\b"),
               (Role.W, r"winger"), (Role.ST, r"striker|\bst\b")]
    for role, pattern in aliases:
        if re.search(pattern, lower):
            brief.role = role
            break
    if "left-foot" in lower or "left foot" in lower:
        brief.constraints.foot = "left"
    if "right-foot" in lower or "right foot" in lower:
        brief.constraints.foot = "right"
    attributes = {"athletic": "athletic", "high line": "high_line", "under pressure": "receives_under_pressure"}
    brief.constraints.attributes = [value for phrase, value in attributes.items() if phrase in lower]
    if "passing" in lower or "breaks lines" in lower:
        if "progressive_passes_p90" in ROLE_SPECS[brief.role].style:
            brief.preferences["progressive_passes_p90"] = 2.0
    warnings = ["Suggestions require coach review; unspecified details keep the structured form defaults"]
    if brief.constraints.attributes:
        warnings.append("Athleticism, high-line defending and pressure reception need separate evidence")
    return brief, warnings


async def interpret(text: str, enabled: bool, model: str):
    fallback, warnings = structured_suggestions(text)
    if not enabled:
        return {"brief": fallback, "method": "structured_rules", "warnings": warnings}
    schema = RecruitmentBrief.model_json_schema()
    try:
        async with httpx.AsyncClient(timeout=25, follow_redirects=False) as client:
            response = await client.post("http://127.0.0.1:11434/api/chat", json={
                "model": model, "stream": False, "format": schema,
                "messages": [{"role": "system", "content": "Convert a coach request to the supplied recruitment schema. Do not invent measurements. Output JSON only."},
                             {"role": "user", "content": text}],
                "options": {"temperature": 0, "num_predict": 700},
            })
            response.raise_for_status()
            if len(response.content) > 100000:
                raise ValueError("Oversized model response")
            result = RecruitmentBrief.model_validate_json(response.json()["message"]["content"])
            if set(result.preferences) - set(ROLE_SPECS[result.role].style) - set(ROLE_SPECS[result.role].quality):
                raise ValueError("Unsupported metric")
            return {"brief": result, "method": "ollama", "warnings": warnings}
    except (httpx.HTTPError, ValidationError, ValueError, KeyError, TypeError):
        return {"brief": fallback, "method": "structured_rules", "warnings": [*warnings, "Language model unavailable or invalid; editable suggestions remain available"]}
