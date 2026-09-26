"""Grounded internal reviewer drafts.

Default: a deterministic assembler that quotes ALL resolution passages of the
selected document (fix for incomplete drafts). An optional LLM provider can
be plugged in; any provider failure falls back to the deterministic draft,
never to an ungrounded answer."""
from __future__ import annotations

from typing import Protocol

from .schemas import Draft, DraftStatus, Passage


class ProviderError(RuntimeError):
    """Base for timeout / outage / rate-limit / malformed output."""


class ProviderTimeout(ProviderError): ...
class ProviderOutage(ProviderError): ...
class ProviderRateLimited(ProviderError): ...
class MalformedGeneration(ProviderError): ...


class Provider(Protocol):
    def complete(self, prompt: str, timeout_s: float) -> str: ...


def assemble_draft(passages: list[Passage], resolution_passages: list[Passage],
                   context_passages: list[Passage] | None = None) -> Draft:
    if not passages:
        return Draft(DraftStatus.NO_EVIDENCE)
    top = passages[0]
    chosen = (context_passages or []) + (resolution_passages or [top])
    lines = [f"Suggested reply (internal draft, based on {top.title}):", ""]
    cites = []
    for p in chosen:
        lines.append(f"{p.text} [{p.citation}]")
        cites.append(p.citation)
    return Draft(DraftStatus.EVIDENCE_ASSEMBLY_COMPLETE, "\n".join(lines),
                 sorted(set(cites)), top.doc_id)


def build_prompt(ticket_text: str, passages: list[Passage], version: str) -> str:
    ctx = "\n".join(f"[{p.citation}] {p.text}" for p in passages)
    return (f"# prompt:{version}\nAnswer ONLY from the documentation below. Cite every "
            f"sentence with its [doc#section] tag. If the docs do not answer, reply "
            f"INSUFFICIENT_EVIDENCE.\n\nDOCS:\n{ctx}\n\nTICKET:\n{ticket_text}\n")


def generate(ticket_text: str, passages: list[Passage], resolution_passages: list[Passage],
             provider: Provider | None, timeout_s: float, version: str,
             context_passages: list[Passage] | None = None) -> tuple[Draft, str | None]:
    """Returns (draft, provider_error_name)."""
    base = assemble_draft(passages, resolution_passages, context_passages)
    if provider is None or base.status is DraftStatus.NO_EVIDENCE:
        return base, None
    try:
        out = provider.complete(build_prompt(ticket_text, passages, version), timeout_s)
        if not isinstance(out, str) or not out.strip():
            raise MalformedGeneration("empty generation")
        if "INSUFFICIENT_EVIDENCE" in out:
            return Draft(DraftStatus.NO_EVIDENCE), None
        cites = sorted({c for p in passages for c in [p.citation] if f"[{c}]" in out})
        if not cites:
            raise MalformedGeneration("generation has no citations")
        return Draft(DraftStatus.EVIDENCE_ASSEMBLY_COMPLETE, out.strip(), cites,
                     base.doc_id), None
    except ProviderError as e:
        return base, type(e).__name__
    except Exception as e:  # unexpected provider bug: still fail safe
        return base, f"UnexpectedProviderError:{type(e).__name__}"
