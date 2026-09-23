"""Deterministic 22-intent and urgency classification.

The production classifier is a reproducible local baseline: TF-IDF text
features with separate logistic-regression models for intent and urgency.
Only ticket subject and body text are training/inference features.
"""

from __future__ import annotations

import hashlib
import json
import re
import threading
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import FeatureUnion, Pipeline


CANONICAL_INTENTS: Tuple[str, ...] = (
    "account_access",
    "api_key_issue",
    "api_usage_question",
    "authentication_failure",
    "billing_query",
    "compliance_request",
    "configuration_help",
    "data_export",
    "data_residency",
    "database_issue",
    "deployment_failure",
    "feature_request",
    "integration_help",
    "onboarding",
    "performance_degradation",
    "quota_or_overage",
    "rate_limit",
    "rollback_request",
    "security_incident",
    "sso_configuration",
    "unclear_request",
    "webhook_issue",
)
CANONICAL_URGENCIES: Tuple[str, ...] = ("high", "low", "medium")
FEATURE_FIELDS: Tuple[str, ...] = ("subject", "body")
MODEL_VERSION = "tfidf-logreg-intent-calibrated-22-v2"
RANDOM_SEED = 42

CALIBRATION_METHOD = "sigmoid"
CALIBRATION_FOLDS = 3

INTENT_WORD_TFIDF_CONFIG = {
    "ngram_range": (1, 2),
    "min_df": 1,
    "sublinear_tf": True,
}

INTENT_CHAR_TFIDF_CONFIG = {
    "analyzer": "char_wb",
    "ngram_range": (3, 5),
    "min_df": 2,
    "sublinear_tf": True,
}

URGENCY_TFIDF_CONFIG = {
    "ngram_range": (1, 1),
    "min_df": 1,
    "sublinear_tf": True,
}

LOGISTIC_REGRESSION_CONFIG = {
    "class_weight": "balanced",
    "max_iter": 2000,
    "multi_class": "ovr",
    "random_state": RANDOM_SEED,
    "solver": "liblinear",
}
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TRAINING_DATA_PATH = PROJECT_ROOT / "data" / "raw" / "development_tickets.json"
PROTECTED_EVALUATION_FILENAMES = {"validation_tickets.json", "final_tickets.json", "hidden_tickets.json"}


def _unwrap_tickets(raw: Any) -> List[Dict[str, Any]]:
    if isinstance(raw, list) and len(raw) == 1 and isinstance(raw[0], list):
        raw = raw[0]
    if not isinstance(raw, list) or not all(isinstance(ticket, dict) for ticket in raw):
        raise ValueError("Classifier training data must be a JSON list of ticket objects")
    return raw


def load_training_tickets(path: Path | str = DEFAULT_TRAINING_DATA_PATH) -> List[Dict[str, Any]]:
    """Load and validate labelled development tickets."""
    resolved = Path(path).resolve()
    if resolved.name.lower() in PROTECTED_EVALUATION_FILENAMES:
        raise ValueError("Classifier training is restricted from validation/final dataset paths")
    raw = json.loads(resolved.read_text(encoding="utf-8"))
    tickets = _unwrap_tickets(raw)
    for index, ticket in enumerate(tickets):
        labels = ticket.get("labels")
        if not isinstance(labels, Mapping):
            raise ValueError(f"Training ticket {index} has no labels object")
        if labels.get("intent") not in CANONICAL_INTENTS:
            raise ValueError(f"Training ticket {index} has unsupported intent label")
        if labels.get("urgency") not in CANONICAL_URGENCIES:
            raise ValueError(f"Training ticket {index} has unsupported urgency label")
        if not ticket_text(ticket):
            raise ValueError(f"Training ticket {index} has no subject/body text")
    return tickets


def ticket_text(ticket: Mapping[str, Any]) -> str:
    """Return the legitimate inference-time text used by both models."""
    metadata = ticket.get("metadata") if isinstance(ticket.get("metadata"), Mapping) else {}
    subject = ticket.get("subject")
    if subject is None:
        subject = metadata.get("original_subject", "")
    body = ticket.get("body")
    if body is None:
        body = ticket.get("raw_content", ticket.get("content", ""))
    return " ".join(part.strip() for part in (str(subject or ""), str(body or "")) if part and part.strip())


def text_group(ticket: Mapping[str, Any]) -> str:
    """Stable duplicate-group key used to prevent train/holdout overlap."""
    return re.sub(r"\s+", " ", ticket_text(ticket).lower()).strip()


def training_data_sha256(path: Path | str = DEFAULT_TRAINING_DATA_PATH) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _intent_pipeline() -> Pipeline:
    features = FeatureUnion(
        [
            (
                "word",
                TfidfVectorizer(
                    **INTENT_WORD_TFIDF_CONFIG
                ),
            ),
            (
                "character",
                TfidfVectorizer(
                    **INTENT_CHAR_TFIDF_CONFIG
                ),
            ),
        ]
    )

    return Pipeline(
        [
            ("features", features),
            (
                "classifier",
                LogisticRegression(
                    **LOGISTIC_REGRESSION_CONFIG
                ),
            ),
        ]
    )


def _urgency_pipeline() -> Pipeline:
    return Pipeline(
        [
            (
                "features",
                TfidfVectorizer(
                    **URGENCY_TFIDF_CONFIG
                ),
            ),
            (
                "classifier",
                LogisticRegression(
                    **LOGISTIC_REGRESSION_CONFIG
                ),
            ),
        ]
    )


def grouped_calibration_splits(
    tickets: Sequence[Mapping[str, Any]],
    labels: Sequence[str],
    *,
    folds: int = CALIBRATION_FOLDS,
    random_seed: int = RANDOM_SEED,
) -> List[Tuple[Any, Any]]:
    """Create deterministic calibration folds with no duplicate-text leakage."""

    if len(tickets) != len(labels):
        raise ValueError(
            "Tickets and labels must have identical lengths"
        )

    if folds < 2:
        raise ValueError(
            "Calibration requires at least two folds"
        )

    texts = [
        ticket_text(ticket)
        for ticket in tickets
    ]

    groups = [
        text_group(ticket)
        for ticket in tickets
    ]

    if any(not group for group in groups):
        raise ValueError(
            "Every calibration ticket must have a non-empty text group"
        )

    splitter = StratifiedGroupKFold(
        n_splits=folds,
        shuffle=True,
        random_state=random_seed,
    )

    splits = list(
        splitter.split(
            texts,
            list(labels),
            groups,
        )
    )

    expected_labels = set(labels)

    for fold_number, (
        train_indices,
        calibration_indices,
    ) in enumerate(splits, start=1):

        train_groups = {
            groups[int(index)]
            for index in train_indices
        }

        calibration_groups = {
            groups[int(index)]
            for index in calibration_indices
        }

        if train_groups & calibration_groups:
            raise RuntimeError(
                "Duplicate text groups leaked across "
                f"calibration fold {fold_number}"
            )

        train_labels = {
            labels[int(index)]
            for index in train_indices
        }

        if train_labels != expected_labels:
            missing = sorted(
                expected_labels - train_labels
            )

            raise ValueError(
                f"Calibration fold {fold_number} training "
                f"partition is missing labels: {missing}"
            )

    return splits


def _calibrated_model(
    tickets: Sequence[Mapping[str, Any]],
    labels: Sequence[str],
    estimator: Pipeline,
) -> CalibratedClassifierCV:
    """Fit one group-safe calibrated classifier."""

    calibration_splits = grouped_calibration_splits(
        tickets,
        labels,
    )

    model = CalibratedClassifierCV(
        estimator=estimator,
        method=CALIBRATION_METHOD,
        cv=calibration_splits,
        ensemble=False,
    )

    model.fit(
        [
            ticket_text(ticket)
            for ticket in tickets
        ],
        list(labels),
    )

    return model


def _model_fingerprint(
    training_sha256: str,
) -> str:
    """Fingerprint the exact training data and classifier specification."""

    material = json.dumps(
        {
            "model_version": MODEL_VERSION,
            "feature_fields": FEATURE_FIELDS,
            "intent_word_tfidf": INTENT_WORD_TFIDF_CONFIG,
            "intent_char_tfidf": INTENT_CHAR_TFIDF_CONFIG,
            "urgency_tfidf": URGENCY_TFIDF_CONFIG,
            "logistic_regression": LOGISTIC_REGRESSION_CONFIG,
            "intent_calibration_method": CALIBRATION_METHOD,
            "intent_calibration_folds": CALIBRATION_FOLDS,
            "urgency_calibration_method": "none",
            "training_data_sha256": training_sha256,
        },
        sort_keys=True,
        default=list,
    ).encode("utf-8")

    return hashlib.sha256(material).hexdigest()


def build_model_bundle(
    tickets: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    """Fit a calibrated intent model and unchanged urgency model."""

    intents = [
        str(ticket["labels"]["intent"])
        for ticket in tickets
    ]

    urgencies = [
        str(ticket["labels"]["urgency"])
        for ticket in tickets
    ]

    if set(intents) != set(CANONICAL_INTENTS):
        missing = sorted(
            set(CANONICAL_INTENTS)
            - set(intents)
        )
        raise ValueError(
            "Training partition does not support "
            f"all canonical intents: {missing}"
        )

    if set(urgencies) != set(CANONICAL_URGENCIES):
        missing = sorted(
            set(CANONICAL_URGENCIES)
            - set(urgencies)
        )
        raise ValueError(
            "Training partition does not support "
            f"all canonical urgencies: {missing}"
        )

    if any(
        not ticket_text(ticket)
        for ticket in tickets
    ):
        raise ValueError(
            "Classifier training requires non-empty subject/body text"
        )

    intent_model = _calibrated_model(
        tickets,
        intents,
        _intent_pipeline(),
    )

    urgency_model = _urgency_pipeline().fit(
        [
            ticket_text(ticket)
            for ticket in tickets
        ],
        urgencies,
    )

    return {
        "intent_model": intent_model,
        "urgency_model": urgency_model,
        "model_version": MODEL_VERSION,
        "training_size": len(tickets),
        "feature_fields": FEATURE_FIELDS,
        "intent_calibration_method": CALIBRATION_METHOD,
        "intent_calibration_folds": CALIBRATION_FOLDS,
        "urgency_calibration_method": "none",
    }


def _ranked_probabilities(model: Any, text: str) -> List[Tuple[str, float]]:
    probabilities = model.predict_proba([text])[0]

    classes = getattr(
        model,
        "classes_",
        None,
    )

    if classes is None and hasattr(model, "named_steps"):
        classes = model.named_steps["classifier"].classes_

    if classes is None:
        raise RuntimeError(
            "Classifier does not expose fitted classes"
        )
    return sorted(
        ((str(label), float(probability)) for label, probability in zip(classes, probabilities)),
        key=lambda item: (-item[1], item[0]),
    )


def predict_with_bundle(bundle: Mapping[str, Any], ticket: Mapping[str, Any]) -> Dict[str, Any]:
    """Classify one valid-text ticket with an already fitted model bundle."""
    text = ticket_text(ticket)
    ranked_intents = _ranked_probabilities(bundle["intent_model"], text)
    ranked_urgencies = _ranked_probabilities(bundle["urgency_model"], text)
    intent, confidence = ranked_intents[0]
    urgency, urgency_confidence = ranked_urgencies[0]
    alternatives = [
        {"intent": label, "confidence": round(probability, 6)}
        for label, probability in ranked_intents[1:4]
    ]
    return {
        "intent": intent,
        "urgency": urgency,
        "confidence": round(confidence, 6),
        "urgency_confidence": round(urgency_confidence, 6),
        "reasoning": (
            "Intent confidence uses group-safe sigmoid calibration; urgency "
            "uses the unchanged TF-IDF logistic-regression head. Both use "
            "subject and body text only."
        ),
        "alternative_intent": alternatives[0]["intent"] if alternatives else None,
        "alternative_intents": alternatives,
        "model_name": MODEL_VERSION,
        "model_version": MODEL_VERSION,
        "intent_calibration_method": bundle.get(
            "intent_calibration_method"
        ),
        "intent_calibration_folds": bundle.get(
            "intent_calibration_folds"
        ),
        "urgency_calibration_method": bundle.get(
            "urgency_calibration_method"
        ),
        "training_data_sha256": bundle.get("training_data_sha256"),
        "model_fingerprint": bundle.get("model_fingerprint"),
    }


def stratified_group_holdout(
    tickets: Sequence[Mapping[str, Any]], random_seed: int = RANDOM_SEED, folds: int = 5
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Create a reproducible intent-stratified holdout with no exact-text overlap."""
    texts = [ticket_text(ticket) for ticket in tickets]
    intents = [ticket["labels"]["intent"] for ticket in tickets]
    groups = [text_group(ticket) for ticket in tickets]
    splitter = StratifiedGroupKFold(n_splits=folds, shuffle=True, random_state=random_seed)
    train_indices, holdout_indices = next(splitter.split(texts, intents, groups))
    train = [dict(tickets[index]) for index in train_indices]
    holdout = [dict(tickets[index]) for index in holdout_indices]
    if {text_group(ticket) for ticket in train} & {text_group(ticket) for ticket in holdout}:
        raise RuntimeError("Duplicate text groups leaked across train and holdout")
    return train, holdout


class TicketClassificationEngine:
    """Classify normalized tickets using one lazily trained process-wide model."""

    _bundle_cache: Dict[str, Dict[str, Any]] = {}
    _cache_lock = threading.Lock()

    def __init__(
        self,
        client: Optional[Any] = None,
        training_data_path: Path | str = DEFAULT_TRAINING_DATA_PATH,
    ):
        # ``client`` remains accepted for public-interface compatibility. The
        # reproducible production baseline is local and does not call it.
        self.client = client
        self.training_data_path = Path(training_data_path)
        self.model_name = MODEL_VERSION

    @property
    def supported_intents(self) -> Tuple[str, ...]:
        return CANONICAL_INTENTS

    @property
    def supported_urgencies(self) -> Tuple[str, ...]:
        return CANONICAL_URGENCIES

    def get_classification_prompt(self, ticket_content: str) -> List[Dict[str, str]]:
        """Retained structured contract for integrations that display a prompt."""
        intents = ", ".join(CANONICAL_INTENTS)
        system_instruction = (
            "Classify one CloudServe ticket into exactly one canonical intent and urgency. "
            f"Intents: [{intents}]. Urgencies: [low, medium, high]. "
            "Return intent, urgency, numeric confidence, and alternatives as JSON."
        )
        return [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": f"Ticket Content:\n{ticket_content}"},
        ]

    def _get_bundle(self) -> Dict[str, Any]:
        resolved = self.training_data_path.resolve()
        data_sha = training_data_sha256(resolved)

        cache_key = (
            f"{resolved}|"
            f"{data_sha}|"
            f"{MODEL_VERSION}"
        )

        bundle = self._bundle_cache.get(
            cache_key
        )

        if bundle is not None:
            return bundle

        with self._cache_lock:
            bundle = self._bundle_cache.get(
                cache_key
            )

            if bundle is None:
                tickets = load_training_tickets(
                    resolved
                )

                bundle = build_model_bundle(
                    tickets
                )

                bundle["training_data_sha256"] = (
                    data_sha
                )

                bundle["model_fingerprint"] = (
                    _model_fingerprint(
                        data_sha
                    )
                )

                self._bundle_cache[
                    cache_key
                ] = bundle

        return bundle

    def process_classification(self, normalized_ticket: Any) -> Dict[str, Any]:
        """Return canonical labels and probability-derived confidence, or fail safely."""
        if not isinstance(normalized_ticket, Mapping):
            return self._fallback("Classifier input must be a mapping")
        text = ticket_text(normalized_ticket)
        if not text.strip():
            return self._fallback("Ticket contains no classifiable subject or body text")
        try:
            bundle = self._get_bundle()
            return predict_with_bundle(bundle, normalized_ticket)
        except Exception as exc:
            return self._fallback("Classifier unavailable", type(exc).__name__)

    @staticmethod
    def _fallback(reason: str, error_type: Optional[str] = None) -> Dict[str, Any]:
        return {
            "failure_code": "CLASSIFICATION_FAILURE",
            "error_type": error_type,
            "intent": "unclear_request",
            "urgency": "medium",
            "confidence": 0.0,
            "urgency_confidence": 0.0,
            "reasoning": reason,
            "alternative_intent": None,
            "alternative_intents": [],
            "model_name": MODEL_VERSION,
            "model_version": MODEL_VERSION,
            "training_data_sha256": None,
        }
