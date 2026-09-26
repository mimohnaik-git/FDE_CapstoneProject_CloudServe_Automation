"""Train intent + urgency classifiers on DEVELOPMENT tickets only.

python -m scripts.train --input data/sample/dev_tickets.json"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.classify import TicketClassifier
from src.config import get_settings
from src.ingest import IngestError, normalize


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, type=Path)
    ap.add_argument("--out", type=Path, default=Path(get_settings().artifacts_dir))
    a = ap.parse_args(argv)
    if "valid" in a.input.name.lower():
        raise SystemExit("Refusing to train on a validation file.")
    data = json.loads(a.input.read_text(encoding="utf-8"))
    data = data["tickets"] if isinstance(data, dict) else data
    texts, intents, urg, answerabilities = [], [], [], []
    for t in data:
        try:
            tk = normalize(t)
        except IngestError:
            continue
        texts.append(tk.text)
        labels = t.get("labels") if isinstance(t.get("labels"), dict) else t
        intents.append(labels["intent"])
        urg.append(labels["urgency"])
        answerabilities.append(labels.get("answerable_from_docs", labels.get("answerable")))
    use_answerability = (answerabilities if all(v is not None for v in answerabilities)
                         else None)
    clf = TicketClassifier.train(texts, intents, urg, use_answerability)
    clf.save(a.out)
    print(f"trained on {len(texts)} tickets; intent calibration={clf.intent.calibration}; "
          f"answerability={'trained' if clf.answerability else 'unavailable'}; "
          f"saved to {a.out}")


if __name__ == "__main__":
    main()
