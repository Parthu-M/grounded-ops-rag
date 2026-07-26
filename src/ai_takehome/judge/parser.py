from __future__ import annotations

import ast
import json
import re
from typing import Any

from pydantic import ValidationError

from ai_takehome.judge.models import PairVerdict, ParsedVerdict

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)
_TRAILING_COMMA_RE = re.compile(r",\s*([}\]])")


def _balanced_object(text: str) -> str | None:
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if escaped:
            escaped = False
            continue
        if char == "\\" and in_string:
            escaped = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    return None


def _validate(data: Any, strategy: str) -> ParsedVerdict:
    try:
        return ParsedVerdict(
            valid=True,
            verdict=PairVerdict.model_validate(data),
            parse_strategy=strategy,
        )
    except ValidationError as exc:
        return ParsedVerdict(
            valid=False,
            parse_error=str(exc),
            parse_strategy=strategy,
        )


def parse_verdict(raw: str) -> ParsedVerdict:
    attempts: list[tuple[str, str]] = [("direct_json", raw.strip())]
    fenced = _FENCE_RE.search(raw)
    if fenced:
        attempts.append(("markdown_fence", fenced.group(1).strip()))
    balanced = _balanced_object(raw)
    if balanced and balanced not in {item[1] for item in attempts}:
        attempts.append(("balanced_object", balanced))

    errors: list[str] = []
    for strategy, candidate in attempts:
        try:
            return _validate(json.loads(candidate), strategy)
        except json.JSONDecodeError as exc:
            errors.append(f"{strategy}: {exc}")
        repaired = _TRAILING_COMMA_RE.sub(r"\1", candidate)
        if repaired != candidate:
            try:
                return _validate(
                    json.loads(repaired), f"{strategy}+trailing_comma_repair"
                )
            except json.JSONDecodeError as exc:
                errors.append(f"{strategy}+repair: {exc}")
        try:
            literal = ast.literal_eval(candidate)
            if isinstance(literal, dict):
                return _validate(literal, f"{strategy}+python_literal")
        except (ValueError, SyntaxError):
            pass
    return ParsedVerdict(
        valid=False,
        parse_error="; ".join(errors) or "No JSON object found",
        parse_strategy="failed",
    )

