"""Metric functions. Every metric returns its numerator and denominator so
reports can never show a percentage without its population."""
from __future__ import annotations

import math
from collections import Counter, defaultdict


def ratio(num: int, den: int) -> dict:
    return {"value": round(num / den, 4) if den else None, "num": num, "den": den}


def classification(y_true: list, y_pred: list, positive: str | None = None) -> dict:
    labels = sorted(set(y_true) | set(y_pred))
    per = {}
    for c in labels:
        tp = sum(t == c and p == c for t, p in zip(y_true, y_pred))
        fp = sum(t != c and p == c for t, p in zip(y_true, y_pred))
        fn = sum(t == c and p != c for t, p in zip(y_true, y_pred))
        pr = tp / (tp + fp) if tp + fp else 0.0
        rc = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * pr * rc / (pr + rc) if pr + rc else 0.0
        per[c] = {"precision": round(pr, 4), "recall": round(rc, 4), "f1": round(f1, 4),
                  "support": sum(t == c for t in y_true)}
    present = [c for c in labels if per[c]["support"] > 0]
    out = {
        "accuracy": ratio(sum(t == p for t, p in zip(y_true, y_pred)), len(y_true)),
        "macro_precision": round(sum(per[c]["precision"] for c in present) / len(present), 4) if present else None,
        "macro_recall": round(sum(per[c]["recall"] for c in present) / len(present), 4) if present else None,
        "macro_f1": round(sum(per[c]["f1"] for c in present) / len(present), 4) if present else None,
        "macro_over_classes": len(present),
        "per_class": per,
    }
    if positive:
        tp = sum(t == positive and p == positive for t, p in zip(y_true, y_pred))
        out[f"{positive}_recall"] = ratio(tp, sum(t == positive for t in y_true))
    return out


def ece(confidences: list[float], correct: list[bool], n_bins: int = 10) -> dict:
    """Expected calibration error with equal-width bins. Reports bin count and
    n, because ECE on small samples is noisy."""
    n = len(confidences)
    if not n:
        return {"value": None, "n": 0, "bins": n_bins, "bands": [],
                "calibration_status": "NOT_ESTABLISHED"}
    bins = defaultdict(list)
    for c, ok in zip(confidences, correct):
        bins[min(int(c * n_bins), n_bins - 1)].append((c, ok))
    total = sum(len(b) / n * abs(sum(x for x, _ in b) / len(b) - sum(o for _, o in b) / len(b))
                for b in bins.values())
    bands_out = []
    for idx in sorted(bins):
        band = bins[idx]
        mean_conf = sum(x for x, _ in band) / len(band)
        observed = sum(bool(o) for _, o in band) / len(band)
        bands_out.append({"low": idx / n_bins, "high": (idx + 1) / n_bins,
                          "n": len(band), "mean_confidence": round(mean_conf, 4),
                          "observed_accuracy": round(observed, 4),
                          "absolute_gap": round(abs(mean_conf - observed), 4)})
    return {"value": round(total, 4), "n": n, "bins": n_bins,
            "non_empty_bins": len(bins), "small_sample_warning": n < 200,
            "bands": bands_out,
            "calibration_status": "NOT_ESTABLISHED" if n < 200 else "MEASURED"}


def retrieval(rankings: list[list[str]], expected: list[set], ks=(1, 3, 5)) -> dict:
    """Document-level. Recall@k = expected docs found in top-k / all expected
    docs (micro). Precision@k = relevant in top-k / k. Only tickets with a
    non-empty expected set are evaluated; that count is reported."""
    pairs = [(r, e) for r, e in zip(rankings, expected) if e]
    expected_docs_total = sum(len(e) for _, e in pairs)
    out: dict[str, object] = {"eligible_tickets": len(pairs),
                              "expected_docs_total": expected_docs_total}
    for k in ks:
        found = sum(len(set(r[:k]) & e) for r, e in pairs)
        out[f"recall@{k}"] = ratio(found, expected_docs_total)
        prec = [len(set(r[:k]) & e) / k for r, e in pairs]
        out[f"precision@{k}"] = round(sum(prec) / len(prec), 4) if prec else None
        hit = sum(bool(set(r[:k]) & e) for r, e in pairs)
        out[f"hit@{k}"] = ratio(hit, len(pairs))
    rr = []
    for r, e in pairs:
        rank = next((i + 1 for i, d in enumerate(r) if d in e), None)
        rr.append(1 / rank if rank else 0.0)
    out["mrr"] = round(sum(rr) / len(rr), 4) if rr else None
    return out


def routing(expected: list[str], predicted: list[str], must_not_auto: list[bool]) -> dict:
    exp_auto = sum(e == "AUTO_RESPOND" for e in expected)
    exp_esc = len(expected) - exp_auto
    false_auto = sum(e == "ESCALATE" and p == "AUTO_RESPOND" for e, p in zip(expected, predicted))
    false_esc = sum(e == "AUTO_RESPOND" and p == "ESCALATE" for e, p in zip(expected, predicted))
    auto = sum(p == "AUTO_RESPOND" for p in predicted)
    true_auto = auto - false_auto
    return {
        "routing_accuracy": ratio(sum(e == p for e, p in zip(expected, predicted)), len(expected)),
        "expected_auto": exp_auto, "expected_escalate": exp_esc,
        "predicted_auto": auto,
        "automation_rate": ratio(auto, len(predicted)),
        "escalation_rate": ratio(len(predicted) - auto, len(predicted)),
        "false_automatic_responses": false_auto,
        "false_escalations": false_esc,
        "auto_precision": ratio(true_auto, auto),
        "auto_recall": ratio(true_auto, exp_auto),
        "must_not_auto_violations": sum(m and p == "AUTO_RESPOND"
                                        for m, p in zip(must_not_auto, predicted)),
        "must_not_auto_tickets": sum(must_not_auto),
    }


def latency(values: list[float], warmup: int = 1) -> dict:
    """Mean/P50/P95 excluding the first `warmup` tickets (model load / cache
    cold start), plus the raw figures, so mean > P95 cannot confuse readers."""
    def summ(v):
        if not v:
            return {"n": 0}
        s = sorted(v)
        pct = lambda q: s[min(len(s) - 1, max(0, math.ceil(q * len(s)) - 1))]
        return {"n": len(s), "mean": round(sum(s) / len(s), 4), "p50": round(pct(.5), 4),
                "p95": round(pct(.95), 4), "max": round(s[-1], 4)}
    return {"steady_state": summ(values[warmup:]), "including_warmup": summ(values),
            "warmup_excluded": min(warmup, len(values)),
            "note": "pipeline processing time only; NOT customer first-response time"}


def subgroup_gate(groups: dict[str, list[bool]], max_gap_pp: float = 5.0,
                  min_n: int = 30) -> dict:
    """Fairness gate on a per-ticket quality signal. Returns NOT_PROVEN when
    any subgroup has fewer than min_n tickets."""
    rows = {g: ratio(sum(v), len(v)) for g, v in groups.items()}
    small = [g for g, v in groups.items() if len(v) < min_n]
    vals = [r["value"] for r in rows.values() if r["value"] is not None]
    gap = round((max(vals) - min(vals)) * 100, 2) if len(vals) > 1 else None
    if small or gap is None:
        status = "NOT_PROVEN"
    else:
        status = "PASS" if gap < max_gap_pp else "FAIL"
    return {"status": status, "gap_pp": gap, "max_gap_pp": max_gap_pp, "min_n": min_n,
            "undersized_groups": small, "groups": rows}


def label_contradictions(texts: list[str], labels: list) -> dict:
    """Normalised duplicate-text groups and those with conflicting labels."""
    import re
    norm = lambda t: re.sub(r"\W+", " ", t.lower()).strip()
    groups = defaultdict(list)
    for t, l in zip(texts, labels):
        groups[norm(t)].append(l)
    dup = {k: v for k, v in groups.items() if len(v) > 1}
    contra = {k: v for k, v in dup.items() if len(set(map(str, v))) > 1}
    return {"tickets": len(texts), "unique_groups": len(groups),
            "duplicate_groups": len(dup), "tickets_in_duplicate_groups": sum(map(len, dup.values())),
            "contradictory_groups": len(contra),
            "tickets_in_contradictory_groups": sum(map(len, contra.values()))}
