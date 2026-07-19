from __future__ import annotations

import argparse

import pytest

from daily_report.main import build_parser, run_integration_serve


def parse(*arguments: str) -> argparse.Namespace:
    return build_parser().parse_args(list(arguments))


def test_integration_provider_is_missing_config_by_default() -> None:
    args = parse("integration", "serve")

    assert args.enabled is None


@pytest.mark.parametrize("value", [None, False])
def test_disabled_integration_exits_silently_before_importing_provider(
    value: bool | None,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    args = argparse.Namespace(enabled=value)
    imported: list[str] = []
    original_import = __import__

    def recording_import(name, *import_args, **import_kwargs):
        if name.startswith("daily_report.integration_v1"):
            imported.append(name)
        return original_import(name, *import_args, **import_kwargs)

    monkeypatch.setattr("builtins.__import__", recording_import)

    run_integration_serve(args)

    assert imported == []
    assert capsys.readouterr() == ("", "")


@pytest.mark.parametrize(
    ("value", "expected"),
    [("true", True), ("false", False), ("TRUE", True), ("0", False)],
)
def test_integration_activation_accepts_only_explicit_booleans(value: str, expected: bool) -> None:
    assert parse("integration", "serve", "--enabled", value).enabled is expected


def test_integration_activation_rejects_misspelled_boolean() -> None:
    with pytest.raises(SystemExit):
        parse("integration", "serve", "--enabled", "tru")


def test_live_test_requires_an_explicit_test_only_switch() -> None:
    args = parse("integration", "live-test", "--runtime-dir", "unused")

    assert args.test_only is False


def test_live_test_profiles_are_fixed_at_parse_time() -> None:
    normal = parse(
        "integration",
        "live-test",
        "--test-only",
        "--runtime-dir",
        "unused",
        "--profile",
        "normal",
    )

    assert normal.profile == "normal"
    with pytest.raises(SystemExit):
        parse(
            "integration",
            "live-test",
            "--test-only",
            "--runtime-dir",
            "unused",
            "--profile",
            "network-controlled-profile",
        )
