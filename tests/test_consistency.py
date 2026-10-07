"""
Offline consistency checks for the shipped plugin, modelled on the jira
sibling plugin's own tests/test_plugin_consistency.py but broader: this
plugin's acceptance criteria also require that no file in the plugin
restates a confluence-as flag or a Confluence concept, and that no
instance fact about this organization appears anywhere in it.

No external dependencies beyond pytest and pyyaml (already installed for
the offline suite): no confluence-as CLI, no Claude Code, no network.
"""

import hashlib
import json
import re
import subprocess
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_MD = REPO_ROOT / "skills" / "confluence" / "SKILL.md"

MAX_NON_BLANK_BODY_LINES = 20
REQUIRED_DEPENDENCY_RANGE = "confluence-as>=2,<3"


def _read_skill_md() -> tuple[dict, str]:
    """Return (parsed frontmatter, body text with frontmatter removed)."""
    text = SKILL_MD.read_text()
    assert text.startswith("---\n"), (
        "skills/confluence/SKILL.md must start with YAML frontmatter (---)"
    )
    _, _, rest = text.partition("---\n")
    frontmatter_text, sep, body = rest.partition("\n---")
    assert sep, "skills/confluence/SKILL.md frontmatter is never closed with ---"
    frontmatter = yaml.safe_load(frontmatter_text)
    return frontmatter, body.lstrip("\n")


def test_skill_frontmatter_parses_and_names_confluence():
    """skills/confluence/SKILL.md's frontmatter parses and names the
    skill 'confluence'."""
    frontmatter, _ = _read_skill_md()
    assert isinstance(frontmatter, dict)
    assert frontmatter.get("name") == "confluence"


def test_skill_body_is_under_twenty_non_blank_lines():
    """
    The skill BODY (frontmatter excluded -- YAML frontmatter is
    metadata, not instructional content, and does not count toward the
    twenty-line limit) is under twenty non-blank lines.
    """
    _, body = _read_skill_md()
    non_blank = [line for line in body.splitlines() if line.strip()]
    assert len(non_blank) < MAX_NON_BLANK_BODY_LINES, (
        f"skills/confluence/SKILL.md body has {len(non_blank)} non-blank "
        f"lines; expected under {MAX_NON_BLANK_BODY_LINES}"
    )


def test_skill_names_the_dependency_range():
    """The skill names the confluence-as major-version range it requires."""
    _, body = _read_skill_md()
    assert REQUIRED_DEPENDENCY_RANGE in body


def _pyproject_version(text: str) -> str:
    """
    Minimal extraction of [project].version without a TOML parser
    dependency: tomllib is Python 3.11+ only, and this repo's CI matrix
    still tests 3.10.
    """
    in_project = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("["):
            in_project = stripped == "[project]"
            continue
        if in_project and stripped.startswith("version"):
            _, _, value = stripped.partition("=")
            return value.strip().strip('"').strip("'")
    raise AssertionError("pyproject.toml: no version = ... found under [project]")


def _manifest_versions() -> dict[str, str]:
    """
    Read every present version-bearing manifest's version field, by
    name, for comparison. Five sites always exist in this repository:
    VERSION, .release-please-manifest.json, pyproject.toml,
    .claude-plugin/plugin.json, and the skill's own frontmatter version.
    .claude-plugin/marketplace.json is checked too, since it exists in
    this repository (unlike some sibling plugins, where it lives only in
    the separate marketplace repo).
    """
    versions: dict[str, str] = {
        "VERSION": (REPO_ROOT / "VERSION").read_text().strip(),
        ".release-please-manifest.json": json.loads(
            (REPO_ROOT / ".release-please-manifest.json").read_text()
        )["."],
        "pyproject.toml": _pyproject_version(
            (REPO_ROOT / "pyproject.toml").read_text()
        ),
        ".claude-plugin/plugin.json": json.loads(
            (REPO_ROOT / ".claude-plugin" / "plugin.json").read_text()
        )["version"],
    }

    frontmatter, _ = _read_skill_md()
    versions["skills/confluence/SKILL.md (frontmatter)"] = frontmatter.get("version")

    marketplace_path = REPO_ROOT / ".claude-plugin" / "marketplace.json"
    if marketplace_path.exists():
        marketplace = json.loads(marketplace_path.read_text())
        # This repository's marketplace.json is flat (a top-level
        # "version", not a nested "metadata" object) -- unlike some
        # sibling plugins' copies, so this reads the shape this file
        # actually has, not one assumed by analogy.
        versions["marketplace.json (top level)"] = marketplace["version"]
        versions["marketplace.json (plugins[0])"] = marketplace["plugins"][0]["version"]

    return versions


def test_manifests_agree_on_one_version():
    """Every present version-bearing manifest must agree on one version."""
    versions = _manifest_versions()
    unique = set(versions.values())
    assert unique == {"3.0.0"}, f"manifest versions must equal 3.0.0: {versions}"


# ---------------------------------------------------------------------------
# Criterion 3: no file in the plugin restates a confluence-as flag or a
# Confluence concept.
#
# Allowed everywhere (never swept for): product names (Confluence,
# Confluence Cloud, confluence-as, Claude Code, Atlassian); the command
# names the hint uses (help, help TOPIC, api search, api describe, api
# topics, api call); the dependency range; instructions about this
# repository itself. None of those are flags or concept words, so the
# patterns below never need to special-case them.
# ---------------------------------------------------------------------------

# Every confluence-as flag this implementation observed against the
# scratch 2.0.0rc1 binary (api describe/--help/--full output across
# every operation this migration exercised), plus the ones named
# explicitly in the acceptance criterion's own examples.
CONFLUENCE_FLAG_PATTERNS = [
    "--confirm",
    "--format",
    "--full",
    "--examples",
    "--id",
    "--transport",
    "--body-format",
    "--field",
    "--space-key",
    "--body",
    "--raw",
    "--representation",
    "--validate-body",
    "--embedded",
    "--private",
    "--root-level",
    "--get-draft",
    "--status",
    "--include-labels",
    "--include-properties",
    "--include-operations",
    "--include-likes",
    "--include-versions",
    "--include-version",
    "--include-favorited-by-current-user-status",
    "--include-webresources",
    "--include-collaborators",
    "--include-direct-children",
    "--cql",
    "--cqlcontext",
    "--cursor",
    "--next",
    "--prev",
    "--limit",
    "--start",
    "--include-archived-spaces",
    "--exclude-current-spaces",
    "--page-id",
    "--property-id",
    "--keys",
    "--ids",
    "--type",
    "--labels",
    "--favorited-by",
    "--not-favorited-by",
    "--sort",
    "--description-format",
    "--offset",
    "--attachment-id",
    "--blogpost-id",
    "--custom-content-id",
    "--parent-id",
]

CONFLUENCE_ENV_VAR_PATTERNS = [
    "CONFLUENCE_SITE_URL",
    "CONFLUENCE_EMAIL",
    "CONFLUENCE_API_TOKEN",
    "CONFLUENCE_AS_TRANSPORT",
    "CONFLUENCE_ALLOWED_SPACES",
    "CONFLUENCE_AS_CASSETTE",
    "CONFLUENCE_MOCK_MODE",
]

# Confluence concept words, per the acceptance criterion's own forbidden
# list (space, page, blog, CQL, label, attachment, comment, template,
# permission, property, watch, hierarchy, analytics, ADF, storage
# format). Matched case-insensitively with word boundaries, stem plus
# any word characters, so a plural/gerund/adjective form is caught too.
CONCEPT_WORD_RE = re.compile(
    r"\b("
    r"space\w*"
    r"|page\w*"
    r"|blog\s*post\w*"
    r"|cql"
    r"|label\w*"
    r"|attachment\w*"
    r"|comment\w*"
    r"|template\w*"
    r"|permission\w*"
    r"|propert\w*"
    r"|watch\w*"
    r"|hierarch\w*"
    r"|analytic\w*"
    r"|adf"
    r"|storage\s+format"
    r")\b",
    re.IGNORECASE,
)

# Paths (repo-relative, POSIX separators) exempt from the flag/concept
# sweep: harness code that must set the transport/allowlist variables
# and can only explain them in code comments, and the task-prompt/
# accept-list and golden-prompt YAML fixtures that live inside it, per
# the acceptance criterion's own exemption list. CHANGELOG.md is
# exempted too: its entries dated before 3.0.0 are historical record
# (allowed to use concept words describing what those releases actually
# did), and this sweep does not parse the file by version heading to
# separate them from the new 3.0.0 entry -- the 3.0.0 entry is written,
# and spot-checked, to name commands only (seat review sign-off, 2026-09-15: the
# 3.0.0 entry may list the deleted skill directory names as a record of
# the deletion; that is not explaining a Confluence concept). `.github/` is NOT exempt: its only concept-stem hits are
# the GitHub Actions `permissions:` key, recorded below as known false
# positives by exact (path, word) pair.
_CONCEPT_SWEEP_EXEMPT_PREFIXES = ("tests/", "skills/confluence/tests/")
_CONCEPT_SWEEP_EXEMPT_FILES = ("CHANGELOG.md",)


def _is_concept_sweep_exempt(rel_path: str) -> bool:
    return rel_path.startswith(_CONCEPT_SWEEP_EXEMPT_PREFIXES) or (
        rel_path in _CONCEPT_SWEEP_EXEMPT_FILES
    )


# A generic English word that collides with a forbidden concept stem, in
# a context that is not documentation explaining Confluence at all:
# legal boilerplate (LICENSE's "Permission is hereby granted...") and a
# tool's own configuration value (ruff's `indent-style = "space"`).
# Recorded explicitly, by exact (path, matched word) pair, rather than
# exempting the whole file, so any OTHER, real hit in the same file
# still fails the sweep.
_CONCEPT_SWEEP_KNOWN_FALSE_POSITIVES = {
    ("LICENSE", "permission"),
    ("pyproject.toml", "space"),
    (".github/workflows/ci.yml", "permission"),
    (".github/workflows/ci.yml", "permissions"),
    (".github/workflows/release.yml", "permission"),
    (".github/workflows/release.yml", "permissions"),
    (".github/workflows/sync-marketplace.yml", "permissions"),
}


def _tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def _read_text_if_possible(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None


def test_no_confluence_as_flag_or_env_var_outside_exempt_files():
    hits = []
    for rel_path in _tracked_files():
        if _is_concept_sweep_exempt(rel_path):
            continue
        text = _read_text_if_possible(REPO_ROOT / rel_path)
        if text is None:
            continue
        for pattern in (*CONFLUENCE_FLAG_PATTERNS, *CONFLUENCE_ENV_VAR_PATTERNS):
            if pattern in text:
                hits.append(f"{rel_path}: {pattern!r}")
    assert not hits, (
        "confluence-as flag/environment-variable names found outside "
        "exempt files:\n" + "\n".join(hits)
    )


def test_no_confluence_concept_word_outside_exempt_files():
    hits = []
    for rel_path in _tracked_files():
        if _is_concept_sweep_exempt(rel_path):
            continue
        text = _read_text_if_possible(REPO_ROOT / rel_path)
        if text is None:
            continue
        for match in CONCEPT_WORD_RE.finditer(text):
            word = match.group(0).lower()
            if (rel_path, word) in _CONCEPT_SWEEP_KNOWN_FALSE_POSITIVES:
                continue
            hits.append(f"{rel_path}: {match.group(0)!r}")
    assert not hits, (
        "Confluence concept words found outside exempt files:\n" + "\n".join(hits)
    )


# ---------------------------------------------------------------------------
# Criterion 4: instance facts about this organization appear nowhere in
# the plugin.
# ---------------------------------------------------------------------------

_JAS_TICKET_RE = re.compile(r"\bJAS-\d+\b")
_GC_TICKET_RE = re.compile(r"\bGC-\d+\b")

# SHA-256 digests of the lower-cased UTF-8 values of the organization's
# sandbox key, maintainer handle, private repository name, two host-wrapper
# names and Atlassian host, keyed by value length. The source holds only
# these digests, never the values or pieces of them. A digest keeps a value
# out of sight, not secret: a short value can be guessed and hashed, and
# none of these is a credential. No value contains whitespace, so every
# occurrence lies inside one run of non-whitespace characters, and hashing
# each window of a listed length in every such run finds it at any position
# and in any letter case.
_INSTANCE_FACT_DIGESTS_BY_LENGTH = {
    3: frozenset({"c98a5865f0e7eee4c5f77ccbc5cb81117c168e28333f6273c1d3b17f9bcff0d4"}),
    9: frozenset({"cfda4dfd4a7fa99804290232c963ad0c8f309415debe4ce98d4eacd5e4d13116"}),
    13: frozenset({"8420a9b39d04aa83549d9c0daa51cb40ef8c1bce3d4cb21392aebb4d7058351a"}),
    19: frozenset({"06f14b2f2daaf3045b9fad98b4d16b5220a0b3814f3b84febb844825e1dcce04"}),
    20: frozenset({"36c4f1e9b111ebfef9e468a9e7a8c4512d96bd57aaf8553d38059c92a8ab155c"}),
    23: frozenset({"3de3f9d8fb48b9e7d25b549a81fd7ffc396a0c18a3b8c507baf22795f66e901f"}),
}
_NON_WHITESPACE_RUN_RE = re.compile(r"\S+")


def _instance_fact_digests_in(text: str, table=None) -> set[str]:
    """Return the digest of every listed instance fact found in text."""
    table = _INSTANCE_FACT_DIGESTS_BY_LENGTH if table is None else table
    found = set()
    for run in _NON_WHITESPACE_RUN_RE.findall(text.lower()):
        for length, digests in table.items():
            for start in range(len(run) - length + 1):
                window = run[start : start + length].encode("utf-8")
                digest = hashlib.sha256(window).hexdigest()
                if digest in digests:
                    found.add(digest)
    return found


def test_instance_fact_matcher_finds_a_value_anywhere_in_any_case():
    """The digest matcher finds a listed value inside a longer token, next
    to punctuation and in other letter cases, and nothing else. A synthetic
    value stands in for the real ones, whose digests alone are in source."""
    value = "example-instance.invalid"
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    table = {len(value): frozenset({digest})}
    for text in (
        value,
        f"see {value}.",
        f"x{value}y",
        f"https://{value.upper()}/path",
        f"('{value.title()}')",
    ):
        assert _instance_fact_digests_in(text, table) == {digest}, text
    for text in ("", "example-instance", "example instance.invalid"):
        assert _instance_fact_digests_in(text, table) == set(), text


def test_no_instance_fact_patterns_anywhere():
    """
    None of this organization's instance-fact patterns appear anywhere
    in the plugin. JAS-prefixed ticket keys are the one pattern allowed
    outside this test in exactly one place: CHANGELOG.md (a release
    history entry may cite the ticket that produced it). Every other
    pattern -- including GC-prefixed ticket keys, which belong to a
    different Jira project entirely and have no legitimate reason to
    appear here at all -- is checked in every tracked file, CHANGELOG.md
    included.
    """
    hits = []
    for rel_path in _tracked_files():
        text = _read_text_if_possible(REPO_ROOT / rel_path)
        if text is None:
            continue
        if _GC_TICKET_RE.search(text):
            hits.append(f"{rel_path}: GC-ticket pattern")
        if rel_path != "CHANGELOG.md" and _JAS_TICKET_RE.search(text):
            hits.append(f"{rel_path}: JAS-ticket pattern")
        for digest in sorted(_instance_fact_digests_in(text)):
            hits.append(f"{rel_path}: instance fact with sha256 {digest[:12]}")
    assert not hits, "instance-fact patterns found:\n" + "\n".join(hits)
