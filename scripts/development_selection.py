"""Development-only grouped model, retrieval, and routing selection audit.

This script never reads Validation-80. It writes reproducible selection evidence
and candidate artifacts to paths supplied by the caller.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
from collections import Counter, defaultdict
from dataclasses import replace
from pathlib import Path

import joblib
import numpy as np
import sklearn
from scipy import sparse
from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import FeatureUnion, Pipeline as SkPipeline

from src import eligibility, generate, guardrails, router
from src.classify import TextClassifier, TicketClassifier
from src.config import get_settings
from src.ingest import normalize
from src.retrieve import Retriever, chunk_articles, load_kb
from src.schemas import Passage, Prediction
from evaluation import metrics as M


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def norm_template(text: str) -> str:
    text = text.lower()
    text = re.sub(r"\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b", " <email> ", text)
    text = re.sub(r"\b(?:[a-f0-9]{8,}|\d+)\b", " <value> ", text)
    return re.sub(r"\W+", " ", text).strip()


class DSU:
    def __init__(self, n: int):
        self.p = list(range(n))

    def find(self, x: int) -> int:
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a: int, b: int) -> None:
        a, b = self.find(a), self.find(b)
        if a != b:
            self.p[b] = a


def build_groups(texts: list[str]) -> tuple[list[int], dict]:
    normalized = [norm_template(t) for t in texts]
    exact = defaultdict(list)
    for i, text in enumerate(normalized):
        exact[text].append(i)
    dsu = DSU(len(texts))
    for indexes in exact.values():
        for i in indexes[1:]:
            dsu.union(indexes[0], i)
    # Practical near-template grouping using sparse character-TF-IDF cosine.
    near_vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=2)
    near_matrix = near_vec.fit_transform(normalized)
    similarities = (near_matrix @ near_matrix.T).tocoo()
    for i, j, score in zip(similarities.row, similarities.col, similarities.data):
        if i < j and score >= 0.88:
            dsu.union(int(i), int(j))
    roots = {}
    groups = []
    for i in range(len(texts)):
        root = dsu.find(i)
        roots.setdefault(root, len(roots))
        groups.append(roots[root])
    sizes = Counter(groups)
    return groups, {
        "normalization": "lowercase; email/numeric-token masking; non-word collapse",
        "near_template_rule": "character-TF-IDF cosine >= 0.88",
        "exact_duplicate_groups": sum(len(v) > 1 for v in exact.values()),
        "template_groups": len(sizes),
        "multi_ticket_template_groups": sum(v > 1 for v in sizes.values()),
        "largest_group": max(sizes.values()),
    }


MODEL_CANDIDATES = {
    "current_c4_balanced_sigmoid": {
        "word": (1, 2), "char": (3, 5), "c": 4.0, "class_weight": "balanced",
        "calibration": "sigmoid",
    },
    "regularized_c1_balanced_sigmoid": {
        "word": (1, 2), "char": (3, 5), "c": 1.0, "class_weight": "balanced",
        "calibration": "sigmoid",
    },
    "expanded_ngrams_c2_balanced_sigmoid": {
        "word": (1, 3), "char": (3, 5), "c": 2.0, "class_weight": "balanced",
        "calibration": "sigmoid",
    },
}


def make_model(spec: dict, seed: int = 13) -> SkPipeline:
    feats = FeatureUnion([
        ("word", TfidfVectorizer(ngram_range=spec["word"], min_df=1,
                                 sublinear_tf=True, lowercase=True)),
        ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=spec["char"],
                                 min_df=1, sublinear_tf=True)),
    ])
    base = LogisticRegression(max_iter=2000, C=spec["c"],
                              class_weight=spec["class_weight"], random_state=seed)
    clf = CalibratedClassifierCV(base, method=spec["calibration"], cv=3)
    return SkPipeline([("feats", feats), ("clf", clf)])


def oof(model_spec: dict, texts: list[str], labels: list[str], groups: list[int],
        intent_context: list[str] | None = None,
        test_intent_context: list[str] | None = None) -> tuple[list[str], list[float], np.ndarray, list[str]]:
    classes = sorted(set(labels))
    pred = [""] * len(labels)
    conf = [0.0] * len(labels)
    all_probs = np.zeros((len(labels), len(classes)))
    splitter = StratifiedGroupKFold(n_splits=3, shuffle=True, random_state=13)
    y = np.asarray(labels)
    g = np.asarray(groups)
    for train, test in splitter.split(texts, y, g):
        train_texts = [texts[i] for i in train]
        test_texts = [texts[i] for i in test]
        if intent_context is not None:
            train_texts = [f"{texts[i]}\n__intent_{intent_context[i]}" for i in train]
            test_ctx = test_intent_context or intent_context
            test_texts = [f"{texts[i]}\n__intent_{test_ctx[i]}" for i in test]
        model = make_model(model_spec)
        model.fit(train_texts, y[train])
        probs = model.predict_proba(test_texts)
        local_classes = list(model.classes_)
        for row, idx in enumerate(test):
            best = int(np.argmax(probs[row]))
            pred[idx] = local_classes[best]
            conf[idx] = float(probs[row, best])
            for col, label in enumerate(local_classes):
                all_probs[idx, classes.index(label)] = probs[row, col]
    return pred, conf, all_probs, classes


def classification_report(truth: list[str], pred: list[str], conf: list[float],
                          positive: str | None = None) -> dict:
    out = M.classification(truth, pred, positive=positive)
    out["confusion_labels"] = sorted(set(truth) | set(pred))
    out["confusion_matrix"] = confusion_matrix(
        truth, pred, labels=out["confusion_labels"]).tolist()
    out["ece"] = M.ece(conf, [a == b for a, b in zip(truth, pred)])
    return out


class ExperimentRetriever:
    def __init__(self, articles: list[dict], name: str, field_weighted: bool,
                 char_features: bool, unique_docs: bool):
        self.name = name
        self.chunks = chunk_articles(articles)
        self.unique_docs = unique_docs
        docs = []
        for c in self.chunks:
            prefix = f"{c['title']} {c['title']} {c['section']} {c['section']}" \
                if field_weighted else f"{c['title']} {c['section']}"
            docs.append(f"{prefix} {c['text']}")
        word = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)
        if char_features:
            self.vec = FeatureUnion([
                ("word", word),
                ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5),
                                         sublinear_tf=True)),
            ])
        else:
            self.vec = word
        self.matrix = self.vec.fit_transform(docs)

    def search(self, query: str, k: int = 5, threshold: float = 0.1) -> list[Passage]:
        q = self.vec.transform([query])
        scores = (self.matrix @ q.T).toarray().ravel()
        order = sorted(range(len(scores)), key=lambda i: (
            -round(float(scores[i]), 6), self.chunks[i]["doc_id"], self.chunks[i]["section"]))
        out, seen = [], set()
        for i in order:
            c = self.chunks[i]
            if scores[i] < threshold or (self.unique_docs and c["doc_id"] in seen):
                continue
            seen.add(c["doc_id"])
            out.append(Passage(c["doc_id"], c["title"], c["section"], c["text"],
                               round(float(scores[i]), 4), list(c["plans"])))
            if len(out) == k:
                break
        return out

    def passages_for(self, doc_id: str, section_prefix: str | None = None) -> list[Passage]:
        return [Passage(c["doc_id"], c["title"], c["section"], c["text"], 0.0,
                        list(c["plans"])) for c in self.chunks
                if c["doc_id"] == doc_id and (section_prefix is None or
                c["section"].lower().startswith(section_prefix.lower()))]


def retrieval_report(ret, texts: list[str], expected: list[set[str]], threshold: float) -> dict:
    rankings = []
    for text in texts:
        passages = ret.search(text, 5, threshold)
        rankings.append(list(dict.fromkeys(p.doc_id for p in passages)))
    return M.retrieval(rankings, expected)


def fit_text_classifier(name: str, spec: dict, texts: list[str], labels: list[str]) -> TextClassifier:
    obj = TextClassifier(name)
    obj.model = make_model(spec)
    obj.model.fit(texts, labels)
    obj.calibration = f"{spec['calibration']}-cv3"
    return obj


def simulate_routes(tickets, texts, intents, iconf, urgencies, uconf,
                    answers, answer_probs, retriever, settings, allowlist,
                    answer_threshold):
    s = replace(settings, customer_release_authorized=True,
                auto_eligible_intents=tuple(allowlist),
                answerability_confidence_threshold=answer_threshold)
    rows = []
    for t, text, il, ic, ul, uc, al, ap in zip(
            tickets, texts, intents, iconf, urgencies, uconf, answers, answer_probs):
        intent = Prediction(il, round(ic, 4), [])
        urgency = Prediction(ul, round(uc, 4), [])
        # Confidence is the selected-class confidence, matching runtime Prediction.
        answer = Prediction(al, round(ap, 4), [])
        passages = retriever.search(text, s.top_k, s.tfidf_retrieval_score_threshold)
        resolution = retriever.passages_for(passages[0].doc_id, "resolution") if passages else []
        ev = eligibility.assess(text, t.get("customer_tier", "unknown"), intent, urgency,
                                passages, s.tfidf_retrieval_score_threshold,
                                s.eligibility_policy, resolution,
                                s.urgent_operational_intents, answer, answer_threshold)
        draft = generate.assemble_draft(passages, resolution) \
            if passages else None
        supporting = list(passages)
        seen = {p.citation for p in supporting}
        supporting.extend(p for p in resolution if p.citation not in seen)
        g = guardrails.check(text, draft, supporting) if draft else None
        route_value, reasons = router.route(text, intent, urgency, passages, ev, g, s,
                                            s.tfidf_retrieval_score_threshold)
        labels = t["labels"]
        expected_route = labels["expected_route"].upper()
        rows.append({"ticket_id": t["ticket_id"], "predicted_intent": il,
                     "route": route_value.value, "expected_route": expected_route,
                     "must_not_auto": bool(labels.get("must_not_auto_respond")),
                     "reasons": reasons, "evidence_flags": ev.flags,
                     "retrieval_ok": bool(passages),
                     "answerability_predicted": al,
                     "answerability_confidence": round(ap, 4)})
    return rows


def route_summary(rows: list[dict]) -> dict:
    expected = [r["expected_route"] for r in rows]
    predicted = [r["route"] for r in rows]
    return M.routing(expected, predicted, [r["must_not_auto"] for r in rows])


def gate_attribution(rows: list[dict], allowlist: set[str], intent_threshold: float,
                     answer_threshold: float) -> dict:
    counts = Counter()
    for r in rows:
        if r["expected_route"] != "AUTO_RESPOND" or r["route"] == "AUTO_RESPOND":
            continue
        reasons, flags = set(r["reasons"]), set(r["evidence_flags"])
        if r["predicted_intent"] not in allowlist:
            counts["intent_not_auto_eligible"] += 1
        if "intent_below_confidence_threshold" in reasons:
            counts["intent_confidence"] += 1
        if "urgent_operational_intent" in reasons or "urgent_operational_state" in flags:
            counts["urgency"] += 1
        if "answerability_not_established" in flags:
            counts["answerability_confidence"] += 1
        if "no_retrieval_above_threshold" in reasons:
            counts["retrieval_threshold"] += 1
        if "evidence_sufficiency_not_established" in reasons:
            counts["evidence_sufficiency"] += 1
        if "requires_account_state" in flags:
            counts["account_or_operational_state"] += 1
        if "plan_mismatch" in flags:
            counts["plan_mismatch"] += 1
        if "guardrail_blocked" in reasons:
            counts["guardrails"] += 1
        if r["must_not_auto"] or "never_automate_intent" in reasons:
            counts["must_not_auto_policy"] += 1
        known = {"intent_not_auto_eligible", "intent_below_confidence_threshold",
                 "urgent_operational_intent", "eligibility_review_required",
                 "evidence_sufficiency_not_established", "no_retrieval_above_threshold",
                 "guardrail_blocked", "never_automate_intent", "safety_keyword"}
        if set(r["reasons"]) - known:
            counts["other_gates"] += 1
    return dict(counts)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--development", type=Path, required=True)
    ap.add_argument("--validation", type=Path, required=True,
                    help="Fingerprint only; contents are deliberately not loaded")
    ap.add_argument("--kb", type=Path, required=True)
    ap.add_argument("--references", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--candidate-artifacts", type=Path, required=True)
    args = ap.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)
    args.candidate_artifacts.mkdir(parents=True, exist_ok=True)

    tickets = json.loads(args.development.read_text(encoding="utf-8"))
    texts = [normalize(t).text for t in tickets]
    labels = [t["labels"] for t in tickets]
    intent_y = [x["intent"] for x in labels]
    urgency_y = [x["urgency"] for x in labels]
    answer_y = ["answerable" if x["answerable_from_docs"] else "not_answerable"
                for x in labels]
    groups, group_audit = build_groups(texts)
    print("development groups built", flush=True)

    group_members = defaultdict(list)
    for i, group in enumerate(groups):
        group_members[group].append(i)
    contradictions = {}
    for name, values in (("intent", intent_y), ("urgency", urgency_y),
                         ("answerability", answer_y)):
        conflicted = [idxs for idxs in group_members.values()
                      if len({values[i] for i in idxs}) > 1]
        contradictions[name] = {
            "groups": len(conflicted), "tickets": sum(map(len, conflicted)),
            "ticket_ids": [[tickets[i]["ticket_id"] for i in idxs] for idxs in conflicted],
        }

    intent_pred, intent_conf, _, _ = oof(
        MODEL_CANDIDATES["current_c4_balanced_sigmoid"], texts, intent_y, groups)
    intent_report = classification_report(intent_y, intent_pred, intent_conf)
    print("intent OOF complete", flush=True)

    urgency_candidates = {}
    urgency_cache = {}
    for name, spec in MODEL_CANDIDATES.items():
        pred, conf, probs, classes = oof(spec, texts, urgency_y, groups,
                                         intent_y, intent_pred)
        report = classification_report(urgency_y, pred, conf, positive="high")
        urgency_candidates[name] = report
        urgency_cache[name] = (pred, conf, probs, classes)
    selected_urgency = max(urgency_candidates, key=lambda name: (
        urgency_candidates[name]["high_recall"]["value"],
        urgency_candidates[name]["macro_f1"],
        -urgency_candidates[name]["ece"]["value"],
        urgency_candidates[name]["accuracy"]["value"]))
    print("urgency candidates complete", flush=True)

    answer_candidates = {}
    answer_cache = {}
    thresholds = [0.65, 0.70, 0.75, 0.80, 0.85, 0.90]
    for name, spec in MODEL_CANDIDATES.items():
        pred, conf, probs, classes = oof(spec, texts, answer_y, groups)
        base = classification_report(answer_y, pred, conf, positive="not_answerable")
        answer_idx = classes.index("answerable")
        threshold_rows = []
        for threshold in thresholds:
            route_answerable = [p >= threshold for p in probs[:, answer_idx]]
            false_answerable = sum(v and truth == "not_answerable"
                                   for v, truth in zip(route_answerable, answer_y))
            true_answerable = sum(v and truth == "answerable"
                                  for v, truth in zip(route_answerable, answer_y))
            threshold_rows.append({
                "threshold": threshold, "false_answerable": false_answerable,
                "true_answerable": true_answerable,
                "answerable_precision": M.ratio(
                    true_answerable, true_answerable + false_answerable),
                "answerable_recall": M.ratio(
                    true_answerable, sum(v == "answerable" for v in answer_y)),
            })
        base["thresholds"] = threshold_rows
        base["false_answerable_raw"] = sum(a == "not_answerable" and p == "answerable"
                                            for a, p in zip(answer_y, pred))
        base["false_unanswerable_raw"] = sum(a == "answerable" and p == "not_answerable"
                                              for a, p in zip(answer_y, pred))
        answer_candidates[name] = base
        answer_cache[name] = (pred, conf, probs, classes)

    # Safety first without selecting a useless always-negative threshold: require
    # at least 50% answerable recall, minimize false-answerable, then maximize
    # true-answerable and prefer the current-compatible model.
    answer_choices = []
    minimum_true_answerable = sum(v == "answerable" for v in answer_y) * 0.50
    for model_name, rep in answer_candidates.items():
        for row in rep["thresholds"]:
            if row["true_answerable"] < minimum_true_answerable:
                continue
            answer_choices.append((row["false_answerable"], -row["true_answerable"],
                                   0 if model_name == "current_c4_balanced_sigmoid" else 1,
                                   model_name, row["threshold"]))
    _, _, _, selected_answer, answer_threshold = min(answer_choices)
    print("answerability candidates complete", flush=True)

    articles = load_kb(args.kb)
    settings = get_settings()
    retrieval_candidates = {
        "current_word_passage": ExperimentRetriever(
            articles, "current_word_passage", False, False, False),
        "field_weighted_word_char_passage": ExperimentRetriever(
            articles, "field_weighted_word_char_passage", True, True, False),
        "field_weighted_word_char_unique_docs": ExperimentRetriever(
            articles, "field_weighted_word_char_unique_docs", True, True, True),
    }
    expected_docs = [set(x.get("expected_doc_ids") or []) for x in labels]
    retrieval_reports = {name: retrieval_report(ret, texts, expected_docs,
                                                 settings.tfidf_retrieval_score_threshold)
                         for name, ret in retrieval_candidates.items()}
    selected_retrieval = max(retrieval_reports, key=lambda name: (
        retrieval_reports[name]["hit@1"]["value"],
        retrieval_reports[name]["recall@5"]["value"],
        retrieval_reports[name]["mrr"]))
    print("retrieval candidates complete", flush=True)

    urg_pred, urg_conf, _, _ = urgency_cache[selected_urgency]
    ans_pred, ans_conf, ans_probs, ans_classes = answer_cache[selected_answer]
    # Runtime confidence is the winning class probability, not P(answerable).
    ans_selected_conf = [max(row) for row in ans_probs]
    chosen_ret = retrieval_candidates[selected_retrieval]
    baseline_allow = set(settings.auto_eligible_intents)
    baseline_rows = simulate_routes(tickets, texts, intent_pred, intent_conf,
                                    urg_pred, urg_conf, ans_pred, ans_selected_conf,
                                    chosen_ret, settings, baseline_allow, answer_threshold)

    per_intent_policy = {}
    additions = []
    for intent in sorted(set(intent_pred) - baseline_allow - set(settings.never_automate_intents)):
        rows = simulate_routes(tickets, texts, intent_pred, intent_conf,
                               urg_pred, urg_conf, ans_pred, ans_selected_conf,
                               chosen_ret, settings, baseline_allow | {intent}, answer_threshold)
        summary = route_summary(rows)
        subset = [r for r in rows if r["predicted_intent"] == intent]
        expected_auto = sum(r["expected_route"] == "AUTO_RESPOND" for r in subset)
        auto_rows = [r for r in subset if r["route"] == "AUTO_RESPOND"]
        true_auto = sum(r["expected_route"] == "AUTO_RESPOND" for r in auto_rows)
        answerable_rows = [r for r in subset if r["answerability_predicted"] == "answerable"
                           and r["answerability_confidence"] >= answer_threshold]
        per_intent_policy[intent] = {
            "ticket_count": len(subset),
            "expected_auto_proportion": M.ratio(expected_auto, len(subset)),
            "false_auto_count": sum(r["expected_route"] != "AUTO_RESPOND" for r in auto_rows),
            "must_not_auto_count": sum(r["must_not_auto"] for r in auto_rows),
            "retrieval_success": M.ratio(sum(r["retrieval_ok"] for r in subset), len(subset)),
            "answerability_precision": M.ratio(
                sum(t["labels"]["answerable_from_docs"] for t, r in zip(tickets, rows)
                    if r in answerable_rows), len(answerable_rows)),
            "route_precision": M.ratio(true_auto, len(auto_rows)),
            "overall_policy": summary,
        }
        if (len(subset) >= 10 and expected_auto / len(subset) >= 0.90 and
                summary["false_automatic_responses"] == 0 and
                summary["must_not_auto_violations"] == 0):
            additions.append(intent)

    selected_allow = baseline_allow | set(additions)
    selected_rows = simulate_routes(tickets, texts, intent_pred, intent_conf,
                                    urg_pred, urg_conf, ans_pred, ans_selected_conf,
                                    chosen_ret, settings, selected_allow, answer_threshold)
    selected_route_summary = route_summary(selected_rows)
    if (selected_route_summary["false_automatic_responses"] or
            selected_route_summary["must_not_auto_violations"]):
        selected_allow = baseline_allow
        selected_rows = baseline_rows
        selected_route_summary = route_summary(selected_rows)
        additions = []

    # Fit frozen development-only candidate artifacts in a separate directory.
    intent_model = fit_text_classifier("intent", MODEL_CANDIDATES[
        "current_c4_balanced_sigmoid"], texts, intent_y)
    urgency_train = [f"{text}\n__intent_{intent}" for text, intent in zip(texts, intent_y)]
    urgency_model = fit_text_classifier("urgency", MODEL_CANDIDATES[selected_urgency],
                                        urgency_train, urgency_y)
    answer_model = fit_text_classifier("answerability", MODEL_CANDIDATES[selected_answer],
                                       texts, answer_y)
    TicketClassifier(intent_model, urgency_model, answer_model).save(args.candidate_artifacts)

    report = {
        "provenance": {
            "development_sha256": sha(args.development),
            "validation_sha256_fingerprint_only": sha(args.validation),
            "kb_sha256": sha(args.kb), "references_sha256": sha(args.references),
            "python_version": platform.python_version(),
            "sklearn_version": sklearn.__version__,
            "selection_uses_validation_labels": False,
            "split": "StratifiedGroupKFold(n_splits=3, shuffle=True, random_state=13)",
        },
        "data_audit": {
            "tickets": len(tickets), "class_distribution": {
                "intent": dict(Counter(intent_y)), "urgency": dict(Counter(urgency_y)),
                "answerability": dict(Counter(answer_y))},
            "groups": group_audit, "contradictions": contradictions,
        },
        "intent_oof": intent_report,
        "urgency": {"candidates": urgency_candidates, "selected": selected_urgency},
        "answerability": {"candidates": answer_candidates, "selected": selected_answer,
                          "selected_threshold": answer_threshold,
                          "selection_rationale": (
                              "require >=50% development answerable recall; minimize false-answerable; "
                              "then maximize true-answerable")},
        "retrieval": {"candidates": retrieval_reports, "selected": selected_retrieval,
                      "threshold": settings.tfidf_retrieval_score_threshold},
        "routing": {
            "baseline_allowlist": sorted(baseline_allow),
            "candidate_intent_evidence": per_intent_policy,
            "selected_allowlist": sorted(selected_allow),
            "additions": sorted(additions),
            "selected_oof": selected_route_summary,
            "false_escalation_gate_attribution": gate_attribution(
                selected_rows, selected_allow, settings.intent_confidence_threshold,
                answer_threshold),
        },
        "frozen_candidate": {
            "intent_model": "current_c4_balanced_sigmoid",
            "urgency_model": selected_urgency,
            "answerability_model": selected_answer,
            "answerability_threshold": answer_threshold,
            "retrieval": selected_retrieval,
            "auto_eligible_intents": sorted(selected_allow),
            "policy_version": settings.eligibility_policy,
            "artifact_sha256": {p.name: sha(p) for p in args.candidate_artifacts.glob("*.joblib")},
        },
    }
    (args.out / "development_selection.json").write_text(
        json.dumps(report, indent=2,
                   default=lambda value: value.item() if hasattr(value, "item") else str(value)),
        encoding="utf-8")
    print(json.dumps(report["frozen_candidate"], indent=2))


if __name__ == "__main__":
    main()
