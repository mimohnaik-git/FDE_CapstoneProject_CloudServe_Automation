"""Guardrails (A6, A7). Each returns a named block so evaluation can count
blocks per guardrail (evidence that at least one demonstrably blocks)."""
from __future__ import annotations

import re

from .schemas import Draft, DraftStatus, GuardrailResult, Passage

_SECRETS = [
    re.compile(r"\b(sk|pk|api|key)[-_][A-Za-z0-9]{16,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\b(?:\d[ -]?){13,16}\b"),                 # card-like numbers
    re.compile(r"password\s*[:=]\s*\S+", re.I),
    re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I),
    re.compile(r"(?<!\d)(?:\+?\d[\d .()-]{7,}\d)(?!\d)"),
    re.compile(r"\b(?:CUST|ACCOUNT|ACCT)[-_ ]?\d{3,}\b", re.I),
]
_INJECTION = re.compile(r"(ignore (all |any )?(previous|prior) instructions|"
                        r"you are now|system prompt|disregard the (rules|policy))", re.I)
_COMMITMENTS = re.compile(r"\b(we will refund|guarantee[ds]?|we promise|"
                          r"credited to your account|sla credit approved|"
                          r"100% uptime)\b", re.I)
_CITE = re.compile(r"\[([A-Za-z0-9_\-]+#[^\]]+)\]")
_WORD = re.compile(r"[a-z0-9]{4,}")

GROUNDING_MIN_OVERLAP = 0.6   # lexical; NOT a semantic hallucination check


def lexical_grounding(draft_text: str, passages: list[Passage]) -> float:
    """Fraction of draft content words present in cited evidence. This is a
    lexical proxy and is reported as such — it does not replace human review."""
    evidence = set(_WORD.findall(" ".join(p.text.lower() for p in passages)))
    body = _CITE.sub(" ", draft_text.lower()).split(":", 1)[-1]
    words = _WORD.findall(body)
    if not words:
        return 0.0
    return sum(w in evidence for w in words) / len(words)


def check(ticket_text: str, draft: Draft,
          supporting_passages: list[Passage]) -> GuardrailResult:
    blocks, details, checks = [], {}, {}
    if draft.status is not DraftStatus.EVIDENCE_ASSEMBLY_COMPLETE:
        return GuardrailResult(False, ["invalid_generation"],
                               {"status": draft.status.value},
                               {"generation_status": {"status": "BLOCK"}})

    # Citation identifiers are controlled metadata (for example DOC-ACCT-001),
    # not customer account numbers; exclude them from private-data scanning.
    private_scan_text = _CITE.sub(" ", draft.text)
    private_block = any(p.search(private_scan_text) for p in _SECRETS)
    checks["private_data_or_secret"] = {"status": "BLOCK" if private_block else "PASS"}
    if private_block:
        blocks.append("private_data_or_secret")
    injection_block = bool(_INJECTION.search(ticket_text))
    checks["prompt_injection"] = {"status": "BLOCK" if injection_block else "PASS"}
    if injection_block:
        blocks.append("prompt_injection")
    commitment_block = bool(_COMMITMENTS.search(draft.text))
    checks["unsupported_commitment"] = {"status": "BLOCK" if commitment_block else "PASS"}
    if commitment_block:
        blocks.append("unsupported_commitment")

    valid = {p.citation for p in supporting_passages}
    cited = _CITE.findall(draft.text)
    bad = [c for c in cited if c not in valid]
    citation_block = not cited or bool(bad)
    checks["citation_integrity"] = {"status": "BLOCK" if citation_block else "PASS"}
    if citation_block:
        blocks.append("citation_integrity")
        details["unresolvable_citations"] = bad

    cited_passages = [p for p in supporting_passages if p.citation in set(cited)]
    g = lexical_grounding(draft.text, cited_passages)
    details["lexical_grounding"] = round(g, 3)
    grounding_block = g < GROUNDING_MIN_OVERLAP
    checks["grounding"] = {"status": "BLOCK" if grounding_block else "PASS",
                            "lexical_overlap": round(g, 3)}
    if grounding_block:
        blocks.append("grounding")
    return GuardrailResult(not blocks, blocks, details, checks)
