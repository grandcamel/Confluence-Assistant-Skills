"""Release packaging and immutable product-wheel validation (no model calls)."""

import argparse
import gzip
import hashlib
import importlib.metadata
import io
import json
import os
import re
import tarfile
import urllib.request
import zipfile
from email.parser import BytesParser
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
VERSION = "3.0.0"
ARCHIVE_FILES = (
    ".claude-plugin/plugin.json",
    ".claude-plugin/marketplace.json",
    "skills/confluence/SKILL.md",
    "README.md",
    "VERSION",
    "LICENSE",
)
MAX_WHEEL_BYTES = 32 * 1024 * 1024


def verify_wheel(path: Path, expected_sha256: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{64}", expected_sha256):
        raise ValueError(
            "A lowercase SHA256 from the reviewed product packet is required"
        )
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha256:
        raise ValueError("Product wheel SHA256 mismatch")
    with zipfile.ZipFile(path) as wheel:
        metadata_files = [
            n for n in wheel.namelist() if n.endswith(".dist-info/METADATA")
        ]
        if len(metadata_files) != 1:
            raise ValueError("Expected exactly one wheel METADATA")
        metadata = BytesParser().parsebytes(wheel.read(metadata_files[0]))
    name = re.sub(r"[-_.]+", "-", metadata.get("Name", "")).lower()
    version = metadata.get("Version", "")
    if name != "confluence-as" or not re.fullmatch(r"2\.\d+\.\d+(?:rc\d+)?", version):
        raise ValueError("Expected a confluence-as 2.x product wheel")
    return version


class HTTPSRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urlsplit(newurl).scheme != "https":
            raise ValueError("Product download redirects must remain HTTPS")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch_wheel(destination: Path) -> Path:
    url = os.environ.get("CLI_WHEEL_URL", "")
    digest = os.environ.get("CLI_WHEEL_SHA256", "")
    parsed = urlsplit(url)
    filename = Path(parsed.path).name
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or not re.fullmatch(r"confluence_as-[A-Za-z0-9_.+-]+\.whl", filename)
        or not re.fullmatch(r"[0-9a-f]{64}", digest)
    ):
        raise ValueError(
            "Configure a public HTTPS wheel URL and SHA256 from the product packet"
        )
    destination.mkdir(parents=True, exist_ok=False)
    path = destination / filename
    opener = urllib.request.build_opener(HTTPSRedirectHandler())
    with opener.open(url, timeout=60) as response:
        data = response.read(MAX_WHEEL_BYTES + 1)
    if len(data) > MAX_WHEEL_BYTES:
        raise ValueError("Product wheel exceeds the download bound")
    path.write_bytes(data)
    verify_wheel(path, digest)
    return path


CORE_SHA256 = "ac4cb0b07effbecff812652a33aea54b036971e883d3fe349428c6d723d90d83"


def verify_core() -> None:
    """Release validation requires the tested non-editable published compiler."""
    core = importlib.metadata.distribution("as-engine")
    direct = json.loads(core.read_text("direct_url.json") or "{}")
    if (
        core.version != "0.1.2"
        or direct.get("dir_info", {}).get("editable")
        or direct.get("archive_info", {}).get("hashes", {}).get("sha256") != CORE_SHA256
    ):
        raise ValueError("Expected the reviewed non-editable as-engine 0.1.2 wheel")


def verify_versions(root: Path = ROOT) -> None:
    plugin = json.loads((root / ".claude-plugin/plugin.json").read_text())
    marketplace = json.loads((root / ".claude-plugin/marketplace.json").read_text())
    manifest = json.loads((root / ".release-please-manifest.json").read_text())
    project = (
        (root / "pyproject.toml")
        .read_text()
        .split("[project]", 1)[1]
        .split("\n[", 1)[0]
    )
    skill = (root / "skills/confluence/SKILL.md").read_text().split("---", 2)[1]
    versions = [
        (root / "VERSION").read_text().strip(),
        plugin["version"],
        marketplace["version"],
        *[item["version"] for item in marketplace["plugins"]],
        manifest["."],
        re.search(r'^version\s*=\s*"([^"]+)"', project, re.M)[1],
        re.search(r"^version:\s*(\S+)", skill, re.M)[1].strip('"').strip("'"),
    ]
    if set(versions) != {VERSION}:
        raise ValueError("All plugin version sites must equal 3.0.0")
    if '"confluence-as>=2,<3"' not in project:
        raise ValueError("Product dependency must remain confluence-as>=2,<3")


def build_archive(output: Path, root: Path = ROOT) -> None:
    verify_versions(root)
    output.parent.mkdir(parents=True, exist_ok=True)
    with (
        output.open("wb") as target,
        gzip.GzipFile(fileobj=target, mode="wb", mtime=0, filename="") as compressed,
        tarfile.open(fileobj=compressed, mode="w") as archive,
    ):
        for name in ARCHIVE_FILES:
            source = root / name
            if source.is_symlink() or not source.is_file():
                raise ValueError(f"Expected regular release input: {name}")
            data = source.read_bytes()
            member = tarfile.TarInfo(name)
            member.size = len(data)
            member.mode = 0o644
            archive.addfile(member, io.BytesIO(data))


CHANGELOG_HEADING_RE = re.compile(r"^## \[(?P<version>[^\]]+)\][^\n]*$", re.M)


def release_notes(root: Path = ROOT) -> str:
    """Return the CHANGELOG.md section for VERSION, without its heading."""
    text = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    headings = list(CHANGELOG_HEADING_RE.finditer(text))
    matches = [i for i, h in enumerate(headings) if h["version"] == VERSION]
    if len(matches) != 1:
        raise ValueError("CHANGELOG.md must have exactly one 3.0.0 section")
    index = matches[0]
    end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
    body = text[headings[index].end() : end].strip()
    if not body:
        raise ValueError("CHANGELOG.md 3.0.0 section is empty")
    return body + "\n"


def archive_summary(archive: Path) -> str:
    """Markdown naming the archive digest and every member's digest."""
    data = archive.read_bytes()
    lines = [
        f"### {archive.name}",
        "",
        f"Archive SHA-256: `{hashlib.sha256(data).hexdigest()}` ({len(data)} bytes)",
        "",
        "Compare the member digests with the reviewed values before approving "
        "`plugin-release`. Matching members decide: the gzip container bytes "
        "can differ between zlib builds.",
        "",
        "| Member | Bytes | SHA-256 |",
        "|---|---|---|",
    ]
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as handle:
        members = handle.getmembers()
        if [m.name for m in members] != list(ARCHIVE_FILES) or not all(
            m.isfile() for m in members
        ):
            raise ValueError("Archive members must equal the release allowlist")
        for member in members:
            digest = hashlib.sha256(handle.extractfile(member).read()).hexdigest()
            lines.append(f"| `{member.name}` | {member.size} | `{digest}` |")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "operation",
        choices=("fetch-wheel", "archive", "verify-core", "notes", "summary"),
    )
    parser.add_argument(
        "path",
        type=Path,
        nargs="?",
        help="wheel directory, archive or notes output, or the archive to summarize",
    )
    args = parser.parse_args()
    if args.operation == "verify-core":
        verify_core()
        return
    if args.path is None:
        parser.error("a path is required for this operation")
    if args.operation == "fetch-wheel":
        fetch_wheel(args.path)
    elif args.operation == "archive":
        build_archive(args.path)
    elif args.operation == "notes":
        args.path.parent.mkdir(parents=True, exist_ok=True)
        args.path.write_text(release_notes(), encoding="utf-8")
    else:
        print(archive_summary(args.path), end="")


if __name__ == "__main__":
    main()
