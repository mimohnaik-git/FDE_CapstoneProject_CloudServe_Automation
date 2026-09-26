"""Intent + urgency classification (A3).

Calibrated TF-IDF / logistic regression on runtime-safe ticket text only
(subject + body; never labels, references or answerability fields)."""
from __future__ import annotations

from collections import Counter
from pathlib import Path

import joblib
import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion, Pipeline

from .schemas import Prediction


def _features() -> FeatureUnion:
    return FeatureUnion([
        ("word", TfidfVectorizer(ngram_range=(1, 2), min_df=1, sublinear_tf=True,
                                 lowercase=True)),
        ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5),
                                 min_df=1, sublinear_tf=True)),
    ])


class TextClassifier:
    """Calibrated classifier returning label, confidence and alternatives."""

    def __init__(self, name: str, n_alternatives: int = 2, seed: int = 13):
        self.name = name
        self.n_alternatives = n_alternatives
        self.seed = seed
        self.model: Pipeline | None = None
        self.calibration = "none"

    def fit(self, texts: list[str], labels: list[str]) -> "TextClassifier":
        if len(set(labels)) < 2:
            raise ValueError(f"{self.name}: need at least 2 classes")
        base = LogisticRegression(max_iter=2000, C=4.0, class_weight="balanced",
                                  random_state=self.seed)
        min_class = min(Counter(labels).values())
        # Calibration needs >= cv samples per class; degrade honestly if not.
        if min_class >= 3:
            clf = CalibratedClassifierCV(base, method="sigmoid", cv=3)
            self.calibration = "sigmoid-cv3"
        else:
            clf = base
            self.calibration = "none (too few samples per class)"
        self.model = Pipeline([("feats", _features()), ("clf", clf)])
        self.model.fit(texts, labels)
        return self

    @property
    def classes(self) -> list[str]:
        return list(self.model.classes_)

    def predict_proba(self, texts: list[str]) -> np.ndarray:
        if self.model is None:
            raise RuntimeError(f"{self.name} classifier is not trained")
        return self.model.predict_proba(texts)

    def predict(self, text: str) -> Prediction:
        probs = self.predict_proba([text])[0]
        order = np.argsort(-probs, kind="stable")
        classes = self.classes
        top = order[0]
        alts = [(classes[i], round(float(probs[i]), 4))
                for i in order[1:1 + self.n_alternatives]]
        return Prediction(label=classes[top], confidence=round(float(probs[top]), 4),
                          alternatives=alts)

    def save(self, path: str | Path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"name": self.name, "model": self.model,
                     "calibration": self.calibration}, path)

    @classmethod
    def load(cls, path: str | Path) -> "TextClassifier":
        blob = joblib.load(path)
        obj = cls(blob["name"])
        obj.model, obj.calibration = blob["model"], blob["calibration"]
        return obj


class TicketClassifier:
    def __init__(self, intent: TextClassifier, urgency: TextClassifier,
                 answerability: TextClassifier | None = None):
        self.intent = intent
        self.urgency = urgency
        self.answerability = answerability

    @classmethod
    def train(cls, texts, intents, urgencies, answerabilities=None) -> "TicketClassifier":
        answerability = None
        if answerabilities is not None:
            labels = ["answerable" if bool(v) else "not_answerable"
                      for v in answerabilities]
            answerability = TextClassifier("answerability").fit(texts, labels)
        urgency_texts = [f"{text}\n__intent_{intent}" for text, intent in zip(texts, intents)]
        return cls(TextClassifier("intent").fit(texts, intents),
                   TextClassifier("urgency").fit(urgency_texts, urgencies), answerability)

    def classify(self, text: str) -> tuple[Prediction, Prediction]:
        intent = self.intent.predict(text)
        urgency = self.urgency.predict(f"{text}\n__intent_{intent.label}")
        return intent, urgency

    def classify_with_answerability(
            self, text: str) -> tuple[Prediction, Prediction, Prediction | None]:
        intent, urgency = self.classify(text)
        answerability = self.answerability.predict(text) if self.answerability else None
        return intent, urgency, answerability

    def save(self, directory: str | Path) -> None:
        d = Path(directory)
        self.intent.save(d / "intent.joblib")
        self.urgency.save(d / "urgency.joblib")
        if self.answerability:
            self.answerability.save(d / "answerability.joblib")

    @classmethod
    def load(cls, directory: str | Path) -> "TicketClassifier":
        d = Path(directory)
        answerability_path = d / "answerability.joblib"
        return cls(TextClassifier.load(d / "intent.joblib"),
                   TextClassifier.load(d / "urgency.joblib"),
                   TextClassifier.load(answerability_path)
                   if answerability_path.exists() else None)
