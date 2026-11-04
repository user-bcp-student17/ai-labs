from importlib.metadata import version
from pathlib import Path

import pytest
from packaging.version import Version

REQUIREMENTS = Path(__file__).resolve().parent.parent / "requirements.txt"
# Versiones mínimas sin advisories según pip-audit (2026-11-02).
MINIMUM_SAFE_VERSIONS = {"urllib3": "2.8.0", "python-multipart": "0.0.31"}


def _pinned_versions() -> dict[str, str]:
    pins = {}
    for line in REQUIREMENTS.read_text(encoding="utf-8").splitlines():
        name, separator, pinned = line.partition("==")
        if separator:
            pins[name.split("[")[0].lower()] = pinned.strip()
    return pins


@pytest.mark.parametrize(("package", "minimum"), MINIMUM_SAFE_VERSIONS.items())
def test_h_api_05_requirements_pin_patched_versions(package: str, minimum: str) -> None:
    assert Version(_pinned_versions()[package]) >= Version(minimum)


@pytest.mark.parametrize(("package", "minimum"), MINIMUM_SAFE_VERSIONS.items())
def test_h_api_05_installed_versions_are_patched(package: str, minimum: str) -> None:
    assert Version(version(package)) >= Version(minimum)


def test_h_api_05_pyjwt_is_declared_and_pinned() -> None:
    assert _pinned_versions()["pyjwt"] == version("PyJWT")
