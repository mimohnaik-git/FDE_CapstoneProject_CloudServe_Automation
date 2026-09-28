import pytest

from scripts import run


def test_parser_supports_unified_commands():
    assert run.build_parser().parse_args(["demo", "mode"]).command == "demo"
    assert run.build_parser().parse_args(["evaluator", "mode"]).command == "evaluator"


def test_ticket_command_is_not_public(capsys):
    with pytest.raises(SystemExit) as exc:
        run.build_parser().parse_args(["ticket", "VAL-0005"])
    assert exc.value.code == 2
    assert "invalid choice" in capsys.readouterr().err


def test_evaluator_parser_accepts_alternate_dataset(tmp_path):
    dataset = tmp_path / "custom-dataset.json"
    args = run.build_parser().parse_args(
        ["evaluator", "mode", "--input", str(dataset)]
    )
    assert args.input == dataset


def test_release_control_stops_without_enabling(capsys):
    with pytest.raises(SystemExit) as exc:
        run._require_auto_release({"customer_release_authorized": False}, "evaluator")
    assert exc.value.code == 2
    assert "will not enable" in capsys.readouterr().out
