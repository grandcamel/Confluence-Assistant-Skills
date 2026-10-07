"""Offline release regressions; fake wheels only, never provider calls."""

import hashlib
import io
import tarfile
import zipfile

import pytest
import yaml

from tests.release_checks import (
    ARCHIVE_FILES,
    CORE_SHA256,
    ROOT,
    HTTPSRedirectHandler,
    archive_summary,
    build_archive,
    fetch_wheel,
    release_notes,
    verify_core,
    verify_versions,
    verify_wheel,
)

RUFF_VERSION = "0.16.10"


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


@pytest.mark.parametrize(
    "version,direct,accepted",
    [
        ("0.1.2", {"archive_info": {"hashes": {"sha256": CORE_SHA256}}}, True),
        ("0.1.3", {"archive_info": {"hashes": {"sha256": CORE_SHA256}}}, False),
        ("0.1.2", {"archive_info": {"hashes": {"sha256": "0" * 64}}}, False),
        ("0.1.2", {"dir_info": {"editable": True}}, False),
        ("0.1.2", {}, False),
    ],
)
def test_installed_core_identity_refuses_unreviewed_distribution(
    monkeypatch, version, direct, accepted
):
    import json

    class Distribution:
        def read_text(self, name):
            assert name == "direct_url.json"
            return json.dumps(direct)

    core = Distribution()
    core.version = version
    monkeypatch.setattr("importlib.metadata.distribution", lambda name: core)
    if accepted:
        verify_core()
    else:
        with pytest.raises(ValueError, match="reviewed non-editable"):
            verify_core()


@pytest.mark.parametrize("name", ["ci.yml", "release.yml"])
def test_validation_pins_and_verifies_published_core(name):
    workflow = _workflow(name)
    assert workflow["env"]["CORE_WHEEL"].endswith("#sha256=" + CORE_SHA256)
    text = (ROOT / ".github/workflows" / name).read_text()
    assert 'pip install "$CORE_WHEEL" .artifacts/*.whl' in text
    assert "python tests/release_checks.py verify-core" in text


def _grants_contents_write(permissions):
    # A job without its own permissions inherits the workflow's; a workflow
    # without permissions inherits the repository default, which may be write.
    if permissions is None or permissions == "write-all":
        return True
    return isinstance(permissions, dict) and permissions.get("contents") == "write"


def test_publish_release_is_the_only_contents_write_job():
    writers = []
    for path in sorted((ROOT / ".github/workflows").glob("*.yml")):
        workflow = _workflow(path.name)
        assert not _grants_contents_write(workflow.get("permissions")), path.name
        for name, job in workflow["jobs"].items():
            permissions = job.get("permissions", workflow["permissions"])
            if _grants_contents_write(permissions):
                writers.append((path.name, name))
    assert writers == [("release.yml", "publish-release")]


def test_release_publish_defaults_false_and_needs_the_environment():
    workflow = _workflow("release.yml")
    publish = workflow["on"]["workflow_dispatch"]["inputs"]["publish"]
    assert publish["type"] == "boolean"
    assert publish["default"] == "false"
    assert workflow["permissions"] == {"contents": "read"}
    job = workflow["jobs"]["publish-release"]
    assert job["permissions"] == {"contents": "write"}
    assert job["environment"] == "plugin-release"
    assert job["needs"] == "test"
    assert job["if"] == "github.ref == 'refs/heads/main' && inputs.publish"


def _runs(job):
    return "\n".join(step.get("run", "") for step in job["steps"])


def test_release_notes_come_from_changelog_and_digests_reach_the_summary():
    workflow = _workflow("release.yml")
    text = (ROOT / ".github/workflows/release.yml").read_text()
    test_runs = _runs(workflow["jobs"]["test"])
    archive = "dist/confluence-assistant-skills-3.0.0.tar.gz"
    assert (
        f'python tests/release_checks.py summary {archive} >> "$GITHUB_STEP_SUMMARY"'
        in test_runs
    )
    assert "python tests/release_checks.py notes notes/release-notes.md" in test_runs
    create = _runs(workflow["jobs"]["publish-release"])
    assert "--notes-file notes/release-notes.md" in create
    assert "--notes " not in create
    assert "Reviewed one-skill plugin release." not in text
    assert "MARKETPLACE_PAT" not in text
    # The identity guard and the notes check run before the tag exists.
    order = [
        'test "$EXPECTED_SHA" = "$GITHUB_SHA"',
        "test -s notes/release-notes.md",
        "-f ref=refs/tags/v3.0.0",
        "gh release create v3.0.0",
    ]
    positions = [create.find(marker) for marker in order]
    assert -1 not in positions
    assert positions == sorted(positions)


@pytest.mark.parametrize("name", ["ci.yml", "release.yml"])
def test_validation_pins_ruff(name):
    text = (ROOT / ".github/workflows" / name).read_text()
    pins = [
        token
        for line in text.splitlines()
        if "pip install" in line
        for token in line.split()
        if token.startswith("ruff")
    ]
    assert pins == [f"ruff=={RUFF_VERSION}"]


def test_release_notes_are_the_changelog_300_section():
    notes = release_notes()
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert notes.strip() in changelog
    assert notes.startswith("### ")
    assert "\n## [" not in notes
    assert "confluence-as>=2,<3" in notes


def test_release_notes_stop_at_the_next_section_and_refuse_bad_input(tmp_path):
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        "# Changelog\n\n## [3.0.0] - d\n\n- new\n\n## [2.0.1] - d\n- old\n"
    )
    assert release_notes(tmp_path) == "- new\n"
    for text, message in (
        ("# Changelog\n\n## [2.0.1] - d\n- old\n", "exactly one"),
        ("## [3.0.0] - d\n- a\n## [3.0.0] - d\n- b\n", "exactly one"),
        ("## [3.0.0] - d\n\n## [2.0.1] - d\n- old\n", "empty"),
    ):
        changelog.write_text(text)
        with pytest.raises(ValueError, match=message):
            release_notes(tmp_path)


def test_archive_summary_names_the_archive_and_every_member_digest(tmp_path):
    archive = tmp_path / "confluence-assistant-skills-3.0.0.tar.gz"
    build_archive(archive)
    summary = archive_summary(archive)
    assert hashlib.sha256(archive.read_bytes()).hexdigest() in summary
    for name in ARCHIVE_FILES:
        data = (ROOT / name).read_bytes()
        row = f"| `{name}` | {len(data)} | `{hashlib.sha256(data).hexdigest()}` |"
        assert row in summary.splitlines()


def test_archive_summary_refuses_members_outside_the_allowlist(tmp_path):
    archive = tmp_path / "other.tar.gz"
    with tarfile.open(archive, "w:gz") as handle:
        member = tarfile.TarInfo("tests/joint_evaluation.py")
        member.size = 1
        handle.addfile(member, io.BytesIO(b"x"))
    with pytest.raises(ValueError, match="allowlist"):
        archive_summary(archive)
