from src.config import get_settings


def test_config_fingerprint_ignores_runtime_paths():
    a = get_settings(
        db_path="runtime/a.sqlite3",
        artifacts_dir="runtime/artifacts-a",
        kb_path="runtime/kb-a.json",
    )
    b = get_settings(
        db_path="runtime/b.sqlite3",
        artifacts_dir="runtime/artifacts-b",
        kb_path="runtime/kb-b.json",
    )

    assert a.fingerprint() == b.fingerprint()


def test_config_fingerprint_changes_for_policy_change():
    a = get_settings(intent_confidence_threshold=0.80)
    b = get_settings(intent_confidence_threshold=0.81)

    assert a.fingerprint() != b.fingerprint()


def test_config_fingerprint_changes_for_release_authorization(monkeypatch):
    monkeypatch.setenv("CLOUDSERVE_AUTO_RESPONSE_ENABLED", "true")
    monkeypatch.setenv("CLOUDSERVE_AUTO_RESPONSE_DISABLED", "false")
    enabled = get_settings()
    assert enabled.customer_release_authorized is True

    monkeypatch.setenv("CLOUDSERVE_AUTO_RESPONSE_DISABLED", "true")
    disabled = get_settings()
    assert disabled.customer_release_authorized is False

    production = get_settings(customer_release_authorized=False)
    controlled_eval = get_settings(customer_release_authorized=True)
    assert production.fingerprint() != controlled_eval.fingerprint()
