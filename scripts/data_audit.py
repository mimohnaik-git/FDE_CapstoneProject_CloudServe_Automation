"""Find duplicate-text groups with contradictory labels in a ticket file.

python -m scripts.data_audit --input data/sample/dev_tickets.json --label answerable"""
import argparse
import json
from pathlib import Path

from src.ingest import IngestError, normalize
from evaluation.metrics import label_contradictions


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, type=Path)
    ap.add_argument("--label", default="answerable")
    a = ap.parse_args(argv)
    data = json.loads(a.input.read_text(encoding="utf-8"))
    data = data["tickets"] if isinstance(data, dict) else data
    texts, labels = [], []
    for t in data:
        try:
            texts.append(normalize(t).text)
            source = t.get("labels") if isinstance(t.get("labels"), dict) else t
            labels.append(source.get(a.label))
        except IngestError:
            pass
    print(json.dumps(label_contradictions(texts, labels), indent=2))


if __name__ == "__main__":
    main()
