#!/usr/bin/env python3
import argparse
import csv
import json
import os
import random
import re
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class ModelConfig:
    name: str
    provider: str
    api_key_env: str
    base_url: str
    model: str


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Batch run prompts across multiple LLM APIs")
    p.add_argument("--config", required=True, help="Path to models json/yaml config")
    p.add_argument("--input", required=True, help="Path to prompts csv/jsonl")
    p.add_argument("--outdir", default="outputs", help="Output directory")
    p.add_argument("--temperature", type=float, default=0.7)
    p.add_argument("--max-tokens", type=int, default=256)
    p.add_argument("--repeats", type=int, default=1, help="Repeat count per (model, prompt)")
    p.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    p.add_argument("--dry-run", action="store_true", help="Do not call APIs")
    return p.parse_args()


def load_rows(path: str) -> list[dict[str, Any]]:
    p = Path(path)
    if p.suffix.lower() == ".csv":
        rows = []
        with p.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                rows.append(r)
        if rows and ("id" not in rows[0] or "prompt" not in rows[0]):
            raise ValueError("CSV must include columns: id, prompt")
        return rows
    if p.suffix.lower() == ".jsonl":
        rows = []
        with p.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
        return rows
    raise ValueError("Only .csv or .jsonl input is supported")


def load_config(path: str) -> tuple[list[ModelConfig], list[str]]:
    p = Path(path)
    with p.open("r", encoding="utf-8") as f:
        if p.suffix.lower() == ".json":
            data = json.load(f)
        else:
            try:
                import yaml
            except ImportError as e:
                raise RuntimeError("YAML config requires pyyaml. Install dependencies or use JSON config.") from e
            data = yaml.safe_load(f)
    models = [ModelConfig(**m) for m in data.get("models", [])]
    extract_fields = data.get("extract_fields", ["attitude_score"])
    return models, extract_fields


def call_model(client, model: str, prompt: str, temperature: float, max_tokens: int) -> str:
    last_err = None
    for i in range(3):
        try:
            rsp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return rsp.choices[0].message.content or ""
        except Exception as e:
            last_err = e
            if i < 2:
                time.sleep(2**i)
    raise RuntimeError(f"API call failed after retries: {last_err}")


def extract_attitude_score(text: str) -> int | None:
    # 优先尝试 JSON
    try:
        payload = json.loads(text)
        if isinstance(payload, dict):
            v = payload.get("attitude_score")
            if isinstance(v, (int, float)):
                iv = int(v)
                if 0 <= iv <= 10:
                    return iv
            if isinstance(v, str) and v.strip().isdigit():
                iv = int(v.strip())
                if 0 <= iv <= 10:
                    return iv
    except json.JSONDecodeError:
        pass

    # 退化匹配文本中的 0-10 单个数字
    for m in re.finditer(r"\b(10|[0-9])\b", text):
        iv = int(m.group(1))
        if 0 <= iv <= 10:
            return iv
    return None


def extract_structured(text: str, extract_fields: list[str]) -> dict[str, Any]:
    result = {k: None for k in extract_fields}

    payload = None
    try:
        loaded = json.loads(text)
        if isinstance(loaded, dict):
            payload = loaded
    except json.JSONDecodeError:
        payload = None

    if payload:
        for k in extract_fields:
            result[k] = payload.get(k)

    if "attitude_score" in result and result["attitude_score"] is None:
        result["attitude_score"] = extract_attitude_score(text)

    return result


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _iter_rows(rows: list[dict[str, Any]], desc: str):
    try:
        from tqdm import tqdm

        return tqdm(rows, desc=desc)
    except Exception:
        return rows


def _build_prompt(base_prompt: str) -> str:
    suffix = (
        "\n\n请严格只返回 JSON，不要返回任何额外文字。"
        "JSON 需至少包含字段："
        '{"attitude_score": <0-10整数>}'
    )
    return f"{base_prompt}{suffix}"


def main() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except Exception:
        pass

    args = parse_args()
    if args.repeats < 1:
        raise ValueError("--repeats must be >= 1")

    random.seed(args.seed)

    models, extract_fields = load_config(args.config)
    rows = load_rows(args.input)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    outdir = Path(args.outdir) / ts
    ensure_dir(outdir)

    raw_path = outdir / "raw_responses.jsonl"
    extracted_path = outdir / "extracted.csv"

    extracted_rows: list[dict[str, Any]] = []

    with raw_path.open("w", encoding="utf-8") as raw_f:
        for m in models:
            api_key = os.getenv(m.api_key_env, "")
            client = None
            if not args.dry_run:
                from openai import OpenAI

                client = OpenAI(api_key=api_key or "DUMMY", base_url=m.base_url)

            for row in _iter_rows(rows, desc=m.name):
                prompt_id = row.get("id")
                prompt = _build_prompt(str(row.get("prompt", "")))
                condition = row.get("condition", "")
                involvement = row.get("involvement", "")
                topic = row.get("topic", "")
                argument_strength = row.get("argument_strength", "")

                for repeat_idx in range(1, args.repeats + 1):
                    t0 = time.perf_counter()
                    err = None

                    if args.dry_run:
                        score = random.randint(0, 10)
                        text = json.dumps(
                            {
                                "attitude_score": score,
                            },
                            ensure_ascii=False,
                        )
                    else:
                        try:
                            if not api_key:
                                raise RuntimeError(f"Missing API key env: {m.api_key_env}")
                            text = call_model(client, m.model, prompt, args.temperature, args.max_tokens)
                        except Exception as e:
                            err = str(e)
                            text = ""

                    latency_ms = int((time.perf_counter() - t0) * 1000)
                    raw_record = {
                        "id": prompt_id,
                        "condition": condition,
                        "involvement": involvement,
                        "topic": topic,
                        "argument_strength": argument_strength,
                        "repeat_index": repeat_idx,
                        "provider": m.provider,
                        "model_name": m.name,
                        "model": m.model,
                        "prompt": prompt,
                        "response_text": text,
                        "latency_ms": latency_ms,
                        "error": err,
                    }
                    raw_f.write(json.dumps(raw_record, ensure_ascii=False) + "\n")

                    fields = extract_structured(text, extract_fields)
                    extracted_rows.append(
                        {
                            "id": prompt_id,
                            "condition": condition,
                            "involvement": involvement,
                            "topic": topic,
                            "argument_strength": argument_strength,
                            "repeat_index": repeat_idx,
                            "provider": m.provider,
                            "model_name": m.name,
                            **fields,
                            "error": err,
                        }
                    )

    with extracted_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(extracted_rows[0].keys()) if extracted_rows else ["id"])
        writer.writeheader()
        writer.writerows(extracted_rows)

    print(f"Done. Outputs in: {outdir}")


if __name__ == "__main__":
    main()
