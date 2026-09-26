"""Process one ticket and print the decision.

python -m scripts.demo --channel email --subject "SSO login" --body "..." """
import argparse
import json

from src.config import get_settings
from src.pipeline import Pipeline


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--channel", default="email")
    ap.add_argument("--subject", default="")
    ap.add_argument("--body", required=True)
    ap.add_argument("--tier", default="unknown")
    a = ap.parse_args()
    p = Pipeline.from_settings(get_settings(db_path=":memory:"))
    d = p.process({"ticket_id": "DEMO-1", "channel": a.channel, "subject": a.subject,
                   "body": a.body, "customer_tier": a.tier}).to_dict()
    print(json.dumps({k: d[k] for k in ("route", "reasons", "intent", "urgency", "evidence",
                                        "draft", "guardrails")}, indent=2))


if __name__ == "__main__":
    main()
