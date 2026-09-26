from types import SimpleNamespace

from src.config import get_settings
from src.pipeline import Pipeline


def make_pipeline():
    pipeline = Pipeline.__new__(Pipeline)

    pipeline.settings = get_settings(
        evidence_resolution_ratio_min=0.40,
        evidence_symptom_margin_max=0.30,
    )

    return pipeline


def passage(section, score):
    return SimpleNamespace(
        section=section,
        score=score,
    )


def test_evidence_ambiguity_blocks_symptom_dominated_evidence():
    pipeline = make_pipeline()

    passages = [
        passage("Symptoms", 0.80),
        passage("Resolution", 0.20),
        passage("Notes", 0.15),
    ]

    assert pipeline._evidence_ambiguous(passages) is True


def test_evidence_ambiguity_allows_stronger_resolution_support():
    pipeline = make_pipeline()

    passages = [
        passage("Symptoms", 0.60),
        passage("Resolution", 0.30),
        passage("Notes", 0.15),
    ]

    assert pipeline._evidence_ambiguous(passages) is False


def test_evidence_ambiguity_allows_resolution_led_evidence():
    pipeline = make_pipeline()

    passages = [
        passage("Resolution", 0.70),
        passage("Symptoms", 0.25),
    ]

    assert pipeline._evidence_ambiguous(passages) is False


def test_evidence_ambiguity_fails_closed_without_passages():
    pipeline = make_pipeline()

    assert pipeline._evidence_ambiguous([]) is True
