"""Release packaging and immutable product-wheel validation (no model calls)."""

import argparse
import gzip
import hashlib
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("fetch-wheel", "archive"))
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.operation == "fetch-wheel":
        fetch_wheel(args.output)
    else:
        build_archive(args.output)


if __name__ == "__main__":
    main()
