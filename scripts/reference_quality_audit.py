"""Audit Reference-200 must-mention misses without using references at runtime."""
from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path

from src.config import get_settings
from src.pipeline import Pipeline
from evaluation.harness import load_tickets, must_mention_match, strip_labels


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--references", type=Path, required=True)
    parser.add_argument("--tickets", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    refs = json.loads(args.references.read_text(encoding="utf-8"))
    tickets = {t["ticket_id"]: t for t in load_tickets(args.tickets)}
    settings = replace(get_settings(), db_path=":memory:")
    pipeline = Pipeline.from_settings(settings)
    rows = []
    for ref in refs:
        ticket = ref.get("ticket") or tickets.get(ref.get("ticket_id"))
        if not ticket:
            continue
        decision = pipeline.process(strip_labels(ticket), run_id="reference-quality-audit").to_dict()
        draft = decision.get("draft") or {}
        text = (draft.get("text") or "").lower()
        mentions = [
            {"expected": phrase, "match": must_mention_match(phrase, text)}
            for phrase in ref.get("must_mention", [])
        ]
        if mentions and not all(item["match"] for item in mentions):
            expected = set(ref.get("expected_doc_ids", []))
            top_doc = decision.get("passages", [{}])[0].get("doc_id") \
                if decision.get("passages") else None
            rows.append({
                "ticket_id": ref.get("ticket_id"),
                "intent": ref.get("intent"),
                "expected_doc_ids": sorted(expected),
                "top_doc_id": top_doc,
                "top_doc_match": top_doc in expected,
                "must_mentions": mentions,
                "draft_text": draft.get("text", ""),
                "citations": draft.get("citations", []),
            })
    payload = {"failed_cases": len(rows), "rows": rows}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"failed_cases": len(rows)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
