"""Offline release regressions; fake wheels only, never provider calls."""

import hashlib
import io
import tarfile
import zipfile

import pytest
import yaml

from tests.release_checks import (
    ARCHIVE_FILES,
    ROOT,
    HTTPSRedirectHandler,
    build_archive,
    fetch_wheel,
    verify_versions,
    verify_wheel,
)


def _wheel(tmp_path, name="confluence-as", version="2.0.0"):
    path = tmp_path / "candidate.whl"
    with zipfile.ZipFile(path, "w") as wheel:
        wheel.writestr(
            "candidate.dist-info/METADATA", f"Name: {name}\nVersion: {version}\n"
        )
    return path, hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.parametrize("version", ["2.0.0", "2.0.0rc1"])
def test_reviewed_product_wheel(tmp_path, version):
    path, digest = _wheel(tmp_path, version=version)
    assert verify_wheel(path, digest) == version


@pytest.mark.parametrize(
    "name,version",
    [("other", "2.0.0"), ("confluence-as", "1.1.1"), ("confluence-as", "3.0.0")],
)
def test_wrong_product_or_major_refused(tmp_path, name, version):
    path, digest = _wheel(tmp_path, name, version)
    with pytest.raises(ValueError, match=r"2\.x"):
        verify_wheel(path, digest)


@pytest.mark.parametrize("digest", ["", "0" * 64, "moving-main", "A" * 64])
def test_missing_or_wrong_digest_refused(tmp_path, digest):
    path, _ = _wheel(tmp_path)
    with pytest.raises(ValueError):
        verify_wheel(path, digest)


def test_duplicate_metadata_refused(tmp_path):
    path, _ = _wheel(tmp_path)
    with zipfile.ZipFile(path, "a") as wheel:
        wheel.writestr(
            "other.dist-info/METADATA", "Name: confluence-as\nVersion: 2.0.0\n"
        )
    with pytest.raises(ValueError, match="exactly one"):
        verify_wheel(path, hashlib.sha256(path.read_bytes()).hexdigest())


@pytest.mark.parametrize(
    "url",
    [
        "",
        "http://example.test/confluence_as-2.0.0-py3-none-any.whl",
        "https://user:password@example.test/confluence_as-2.0.0-py3-none-any.whl",
        "https://example.test/confluence_as-2.0.0-py3-none-any.whl?token=value",
        "https://example.test/main",
    ],
)
def test_invalid_artifact_binding_refuses_before_network(tmp_path, monkeypatch, url):
    monkeypatch.setenv("CLI_WHEEL_URL", url)
    monkeypatch.setenv("CLI_WHEEL_SHA256", "0" * 64)
    monkeypatch.setattr(
        "urllib.request.build_opener", lambda *_: pytest.fail("network attempted")
    )
    with pytest.raises(ValueError, match="public HTTPS"):
        fetch_wheel(tmp_path / "download")


def test_fetch_verifies_downloaded_wheel(tmp_path, monkeypatch):
    source, digest = _wheel(tmp_path)
    monkeypatch.setenv(
        "CLI_WHEEL_URL", "https://example.test/confluence_as-2.0.0-py3-none-any.whl"
    )
    monkeypatch.setenv("CLI_WHEEL_SHA256", digest)

    class FakeOpener:
        def open(self, url, timeout):
            return io.BytesIO(source.read_bytes())

    monkeypatch.setattr("urllib.request.build_opener", lambda *_: FakeOpener())
    result = fetch_wheel(tmp_path / "download")
    assert verify_wheel(result, digest) == "2.0.0"


def test_redirect_downgrade_refused():
    with pytest.raises(ValueError, match="HTTPS"):
        HTTPSRedirectHandler().redirect_request(
            None, None, 302, "", {}, "http://example.test/wheel"
        )


def test_archive_is_reproducible_and_ships_only_adopted_skill(tmp_path):
    first, second = tmp_path / "one.tar.gz", tmp_path / "two.tar.gz"
    build_archive(first)
    build_archive(second)
    assert first.read_bytes() == second.read_bytes()
    with tarfile.open(first) as archive:
        assert set(archive.getnames()) == set(ARCHIVE_FILES)
        for member in archive.getmembers():
            assert member.isfile()
            assert (
                archive.extractfile(member).read() == (ROOT / member.name).read_bytes()
            )
        assert [n for n in archive.getnames() if n.startswith("skills/")] == [
            "skills/confluence/SKILL.md"
        ]


def test_archive_refuses_version_drift(tmp_path):
    for name in (*ARCHIVE_FILES, "pyproject.toml", ".release-please-manifest.json"):
        destination = tmp_path / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((ROOT / name).read_bytes())
    (tmp_path / "VERSION").write_text("3.0.1\n")
    with pytest.raises(ValueError, match=r"3\.0\.0"):
        build_archive(tmp_path / "archive.tar.gz", tmp_path)


def test_all_version_sites_equal_300():
    verify_versions()


def _workflow(name):
    # BaseLoader keeps the Actions 'on' key as a string (YAML 1.1 treats it as bool).
    return yaml.load(
        (ROOT / ".github/workflows" / name).read_text(), Loader=yaml.BaseLoader
    )


@pytest.mark.parametrize(
    "name,environment",
    [("release.yml", "plugin-release"), ("sync-marketplace.yml", "marketplace-review")],
)
def test_outward_workflows_manual_and_guarded(name, environment):
    workflow = _workflow(name)
    assert set(workflow["on"]) == {"workflow_dispatch"}
    text = (ROOT / ".github/workflows" / name).read_text()
    assert "release-please-action" not in text
    assert "gh pr merge" not in text
    assert "--clobber" not in text
    assert environment in text
    assert "github.ref == 'refs/heads/main'" in text
    assert "EXPECTED_SHA" in text and "GITHUB_SHA" in text


@pytest.mark.parametrize("name", ["ci.yml", "release.yml"])
def test_validation_requires_bound_cli_wheel_and_paid_collection_only(name):
    text = (ROOT / ".github/workflows" / name).read_text()
    assert "vars.CONFLUENCE_CLI_WHEEL_URL" in text
    assert "vars.CONFLUENCE_CLI_WHEEL_SHA256" in text
    assert "python tests/release_checks.py fetch-wheel" in text
    assert 'pip install --pre "confluence-as' not in text
    assert "--collect-only" in text
    assert "ruff check . --output-format=github || true" not in text
