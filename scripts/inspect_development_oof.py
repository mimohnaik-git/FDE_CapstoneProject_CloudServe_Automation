"""Replay the frozen, group-isolated development routing evidence only.

This tool performs no candidate selection and does not read Validation-80.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.config import get_settings
from src.ingest import normalize
from src.retrieve import load_kb
from scripts.development_selection import (MODEL_CANDIDATES, ExperimentRetriever,
                                           build_groups, oof, route_summary,
                                           simulate_routes)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--development", type=Path, required=True)
    ap.add_argument("--kb", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--allowlist", nargs="*", default=None)
    args = ap.parse_args(argv)

    tickets = json.loads(args.development.read_text(encoding="utf-8"))
    texts = [normalize(t).text for t in tickets]
    labels = [t["labels"] for t in tickets]
    intent_y = [x["intent"] for x in labels]
    urgency_y = [x["urgency"] for x in labels]
    answer_y = ["answerable" if x["answerable_from_docs"] else "not_answerable"
                for x in labels]
    groups, group_audit = build_groups(texts)
    spec = MODEL_CANDIDATES["current_c4_balanced_sigmoid"]
    intent, intent_conf, _, _ = oof(spec, texts, intent_y, groups)
    urgency, urgency_conf, _, _ = oof(spec, texts, urgency_y, groups,
                                       intent_y, intent)
    answer, answer_conf, _, _ = oof(spec, texts, answer_y, groups)
    settings = get_settings()
    allowlist = set(args.allowlist) if args.allowlist is not None \
        else set(settings.auto_eligible_intents)
    ret = ExperimentRetriever(load_kb(args.kb),
                               "field_weighted_word_char_unique_docs", True, True, True)
    rows = simulate_routes(tickets, texts, intent, intent_conf, urgency,
                           urgency_conf, answer, answer_conf, ret, settings,
                           allowlist, settings.answerability_confidence_threshold)
    group_ticket_ids: dict[str, list[str]] = {}
    for ticket, group in zip(tickets, groups):
        group_ticket_ids.setdefault(str(group), []).append(str(ticket["ticket_id"]))

    for index, (row, ticket, group) in enumerate(zip(rows, tickets, groups)):
        group_id = str(group)
        row["group_id"] = group_id
        row["group_ticket_ids"] = group_ticket_ids[group_id]
        row["source_intent"] = ticket["labels"]["intent"]
        row["source_urgency"] = ticket["labels"]["urgency"]
        row["source_answerable"] = ticket["labels"]["answerable_from_docs"]
        row["expected_doc_ids"] = ticket["labels"].get("expected_doc_ids", [])
        row["predicted_intent_confidence"] = round(intent_conf[index], 4)
        row["predicted_urgency"] = urgency[index]
        row["predicted_urgency_confidence"] = round(urgency_conf[index], 4)
        passages = ret.search(
            texts[index], settings.top_k, settings.tfidf_retrieval_score_threshold
        )
        row["retrieval_passages"] = [
            {
                "doc_id": passage.doc_id,
                "section": passage.section,
                "score": round(passage.score, 4),
                "citation": passage.citation,
                "plans": passage.plans,
            }
            for passage in passages
        ]
    payload = {"group_audit": group_audit, "allowlist": sorted(allowlist),
               "summary": route_summary(rows), "rows": rows}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload["summary"], indent=2))


if __name__ == "__main__":
    main()
