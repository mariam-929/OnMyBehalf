"""Per-model Groq adapters (A01: the two candidates are NOT drop-in).

Verified against Groq docs 2026-07-25:
  - openai/gpt-oss-120b : strict `json_schema` structured outputs; reasoning_effort low|medium|high.
  - qwen/qwen3.6-27b    : JSON Object Mode only (no schema enforcement) -> Pydantic validate +
                          one repair retry is load-bearing; reasoning_effort none|default +
                          reasoning_format parsed. (Preview model.)

Each adapter exposes `.complete(system, user, schema_model) -> (obj, meta)` returning a validated
Pydantic instance and a meta dict (latency, rate-limit headers, repaired flag).
"""
from __future__ import annotations

import json
import time
from typing import Type

from groq import Groq
from pydantic import BaseModel, ValidationError


def _strictify(node):
    """Groq/OpenAI strict json_schema requires every object to set
    additionalProperties:false and list all its properties in `required`."""
    if isinstance(node, dict):
        props = node.get("properties")
        if props is not None:
            node["additionalProperties"] = False
            node["required"] = list(props.keys())
        for v in node.values():
            _strictify(v)
    elif isinstance(node, list):
        for v in node:
            _strictify(v)
    return node


class BaseAdapter:
    model_id: str

    def __init__(self, client: Groq):
        self.client = client

    def _schema(self, model: Type[BaseModel], strict: bool = False) -> dict:
        schema = model.model_json_schema()
        return _strictify(schema) if strict else schema

    def complete(self, system: str, user: str, schema_model: Type[BaseModel]):
        raise NotImplementedError


class GptOssAdapter(BaseAdapter):
    model_id = "openai/gpt-oss-120b"

    def complete(self, system, user, schema_model, reasoning_effort="medium"):
        t0 = time.time()
        resp = self.client.chat.completions.with_raw_response.create(
            model=self.model_id,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            reasoning_effort=reasoning_effort,
            response_format={
                "type": "json_schema",
                "json_schema": {"name": schema_model.__name__, "strict": True,
                                "schema": self._schema(schema_model, strict=True)},
            },
        )
        headers = resp.headers
        completion = resp.parse()
        content = completion.choices[0].message.content
        obj = schema_model.model_validate_json(content)  # strict decoding should already comply
        meta = _meta(t0, headers, repaired=False)
        return obj, meta


class Qwen36Adapter(BaseAdapter):
    model_id = "qwen/qwen3.6-27b"

    def complete(self, system, user, schema_model, reasoning_effort="default"):
        t0 = time.time()
        # No strict schema -> ask for a JSON object, then validate + one repair retry.
        sys_full = system + "\n\nRespond ONLY with a single JSON object matching the required schema."
        for attempt in range(2):
            resp = self.client.chat.completions.with_raw_response.create(
                model=self.model_id,
                messages=[{"role": "system", "content": sys_full}, {"role": "user", "content": user}],
                reasoning_effort=reasoning_effort,
                reasoning_format="parsed",
                response_format={"type": "json_object"},
            )
            headers = resp.headers
            content = resp.parse().choices[0].message.content
            try:
                obj = schema_model.model_validate_json(content)
                return obj, _meta(t0, headers, repaired=(attempt == 1))
            except ValidationError as e:
                if attempt == 1:
                    raise
                user = (user + f"\n\nYour previous reply failed validation: {e}. "
                        "Return corrected JSON only.")
        raise RuntimeError("unreachable")


def _meta(t0, headers, repaired):
    def h(k):
        try:
            return headers.get(k)
        except Exception:
            return None
    return {
        "latency_s": round(time.time() - t0, 3),
        "repaired": repaired,
        "limit_tpm": h("x-ratelimit-limit-tokens"),
        "remaining_tpm": h("x-ratelimit-remaining-tokens"),
        "limit_rpm": h("x-ratelimit-limit-requests"),
    }


def get_adapter(model_id: str, client: Groq) -> BaseAdapter:
    if model_id.startswith("openai/gpt-oss"):
        return GptOssAdapter(client)
    if model_id.startswith("qwen/"):
        return Qwen36Adapter(client)
    raise ValueError(f"No adapter for model_id={model_id!r}")
