import pytest

from src.ingest import IngestError, normalize
from src.schemas import Channel


def test_email_strips_signature_and_quotes():
    t = normalize({"ticket_id": "1", "channel": "email", "subject": "Hi",
                   "body": "Need help\n> old quoted\n-- \nJohn"})
    assert t.channel is Channel.EMAIL and "quoted" not in t.body and "John" not in t.body


def test_chat_keeps_only_customer_messages():
    t = normalize({"ticket_id": "2", "channel": "live_chat", "messages": [
        {"role": "customer", "text": "db down"}, {"role": "agent", "text": "checking"}]})
    assert t.channel is Channel.CHAT and "checking" not in t.body


def test_docs_comment_uses_page_title():
    t = normalize({"ticket_id": "3", "channel": "docs_comment", "page_title": "SSO",
                   "body": "<b>unclear</b> step"})
    assert "SSO" in t.subject and "<b>" not in t.body


def test_forum_uses_title():
    t = normalize({"ticket_id": "4", "channel": "forum", "title": "429s", "body": "rate"})
    assert t.channel is Channel.FORUM and t.subject == "429s"


@pytest.mark.parametrize("raw", [
    None, "text", {}, {"ticket_id": "x", "channel": "fax", "body": "a"},
    {"ticket_id": "x", "channel": "email", "body": "   "},
    {"ticket_id": "x", "channel": "chat", "messages": "notalist"},
    {"channel": "email", "body": "no id"},
])
def test_malformed_inputs_raise(raw):
    with pytest.raises(IngestError):
        normalize(raw)


def test_oversized_body_truncated():
    t = normalize({"ticket_id": "5", "channel": "email", "body": "a " * 20000})
    assert len(t.body) <= 20000


def test_original_text_preserved_separately_from_clean_processing_text():
    raw = {"ticket_id": "6", "channel": "email", "subject": "Hello",
           "body": "Need <b>help</b>\n> quoted text\n-- \nSignature"}
    t = normalize(raw)
    assert t.original_text == "Hello\n" + raw["body"]
    assert "<b>" not in t.text and "quoted text" not in t.text
