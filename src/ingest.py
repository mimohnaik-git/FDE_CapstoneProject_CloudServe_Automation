"""Channel ingestion and normalisation (A2).

Each channel has its own raw shape. All are normalised to Ticket.
Malformed input raises IngestError; the pipeline turns that into a
logged ESCALATE rather than a crash (A11)."""
from __future__ import annotations

import html
import re

from .schemas import Channel, Ticket

MAX_BODY_CHARS = 20_000
_TAG = re.compile(r"<[^>]+>")
_QUOTED = re.compile(r"^\s*>.*$", re.MULTILINE)
_SIG = re.compile(r"\n--\s*\n.*", re.DOTALL)
_WS = re.compile(r"[ \t]+")


class IngestError(ValueError):
    pass


def _clean(text: str) -> str:
    text = html.unescape(_TAG.sub(" ", text or ""))
    text = _WS.sub(" ", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _require(raw: dict, *keys):
    missing = [k for k in keys if not str(raw.get(k) or "").strip()]
    if missing:
        raise IngestError(f"missing fields: {missing}")


def _email(raw: dict) -> tuple[str, str]:
    _require(raw, "body")
    body = _SIG.sub("", raw["body"])
    body = _QUOTED.sub("", body)
    return raw.get("subject", ""), body


def _chat(raw: dict) -> tuple[str, str]:
    msgs = raw.get("messages")
    if msgs:
        if not isinstance(msgs, list):
            raise IngestError("chat messages must be a list")
        cust = [m.get("text", "") for m in msgs
                if isinstance(m, dict) and m.get("role", "customer") == "customer"]
        body = "\n".join(cust)
    else:
        _require(raw, "body")
        body = raw["body"]
    return raw.get("subject", "Live chat"), body


def _docs_comment(raw: dict) -> tuple[str, str]:
    _require(raw, "body")
    page = raw.get("page_title") or raw.get("subject") or ""
    return f"Docs comment: {page}".strip(), raw["body"]


def _forum(raw: dict) -> tuple[str, str]:
    _require(raw, "body")
    return raw.get("title") or raw.get("subject", ""), raw["body"]


_PARSERS = {
    Channel.EMAIL: _email,
    Channel.CHAT: _chat,
    Channel.DOCS_COMMENT: _docs_comment,
    Channel.FORUM: _forum,
}

_ALIASES = {"live_chat": "chat", "documentation_comment": "docs_comment",
            "doc_comment": "docs_comment", "community_forum": "forum"}


def normalize(raw: dict) -> Ticket:
    if not isinstance(raw, dict):
        raise IngestError("ticket must be an object")
    tid = str(raw.get("ticket_id") or raw.get("id") or "").strip()
    if not tid:
        raise IngestError("missing ticket_id")
    ch = str(raw.get("channel", "")).strip().lower()
    ch = _ALIASES.get(ch, ch)
    try:
        channel = Channel(ch)
    except ValueError as e:
        raise IngestError(f"unknown channel: {raw.get('channel')!r}") from e
    original_subject = str(raw.get("subject") or raw.get("title") or
                           raw.get("page_title") or "")
    if isinstance(raw.get("messages"), list):
        original_body = "\n".join(str(m.get("text") or "") for m in raw["messages"]
                                  if isinstance(m, dict))
    else:
        original_body = str(raw.get("body") or "")
    original_text = f"{original_subject}\n{original_body}".strip()
    subject, body = _PARSERS[channel](raw)
    subject, body = _clean(subject), _clean(body)
    if not body:
        raise IngestError("empty body after normalisation")
    if len(body) > MAX_BODY_CHARS:
        body = body[:MAX_BODY_CHARS]
    return Ticket(
        ticket_id=tid, channel=channel, subject=subject, body=body,
        original_text=original_text,
        customer_tier=str(raw.get("customer_tier") or "unknown").lower(),
        metadata={k: v for k, v in raw.items()
                  if k in ("created_at", "received_at", "customer_id", "product",
                           "customer_region", "language_fluency")},
    )
