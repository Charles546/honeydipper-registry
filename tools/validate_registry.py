#!/usr/bin/env python3
"""Validate Honeydipper driver registry manifests without external dependencies."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

SHA256_RE = re.compile(r"^[a-f0-9]{64}$")


def fail(msg: str) -> None:
    print(f"ERROR: {msg}")


def load_json(path: pathlib.Path) -> object:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def validate_url(value: str, path: str) -> bool:
    parsed = urllib.parse.urlparse(value)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        fail(f"{path}: invalid URL '{value}'")
        return False
    return True


def maybe_probe_url(value: str, path: str, timeout: int) -> bool:
    req = urllib.request.Request(value, method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status < 200 or resp.status >= 400:
                fail(f"{path}: URL returned status {resp.status} for {value}")
                return False
    except urllib.error.HTTPError as e:
        fail(f"{path}: URL returned status {e.code} for {value}")
        return False
    except Exception as e:  # noqa: BLE001
        fail(f"{path}: URL probe failed for {value}: {e}")
        return False
    return True


def maybe_verify_sha(value: str, expected_sha: str, path: str, timeout: int) -> bool:
    hasher = hashlib.sha256()
    try:
        with urllib.request.urlopen(value, timeout=timeout) as resp:
            while True:
                chunk = resp.read(64 * 1024)
                if not chunk:
                    break
                hasher.update(chunk)
    except Exception as e:  # noqa: BLE001
        fail(f"{path}: unable to download {value} for checksum: {e}")
        return False

    actual = hasher.hexdigest()
    if actual != expected_sha:
        fail(f"{path}: sha256 mismatch for {value}: expected {expected_sha} got {actual}")
        return False
    return True


def validate_manifest(
    path: pathlib.Path,
    data: object,
    check_urls: bool,
    check_mirrors: bool,
    check_sha: bool,
    timeout: int,
) -> bool:
    ok = True
    if not isinstance(data, dict):
        fail(f"{path}: manifest root must be an object")
        return False

    for field in ("driver", "latest", "channels", "versions"):
        if field not in data:
            fail(f"{path}: missing required field '{field}'")
            ok = False

    driver = data.get("driver")
    if not isinstance(driver, str) or not driver:
        fail(f"{path}: 'driver' must be a non-empty string")
        ok = False

    stem = path.stem
    if isinstance(driver, str) and driver and stem != driver:
        fail(f"{path}: file name '{stem}.json' does not match driver '{driver}'")
        ok = False

    channels = data.get("channels")
    if not isinstance(channels, dict):
        fail(f"{path}: 'channels' must be an object")
        ok = False

    versions = data.get("versions")
    if not isinstance(versions, dict) or not versions:
        fail(f"{path}: 'versions' must be a non-empty object")
        ok = False
        return ok

    if isinstance(data.get("latest"), str) and data["latest"] not in versions:
        fail(f"{path}: 'latest' points to unknown version '{data['latest']}'")
        ok = False

    if isinstance(channels, dict):
        for channel, version in channels.items():
            if not isinstance(channel, str) or not channel:
                fail(f"{path}: channel names must be non-empty strings")
                ok = False
            if not isinstance(version, str) or version not in versions:
                fail(f"{path}: channel '{channel}' points to missing version '{version}'")
                ok = False

    for version, version_data in versions.items():
        version_path = f"{path}:{version}"
        if not isinstance(version_data, dict):
            fail(f"{version_path}: version entry must be an object")
            ok = False
            continue

        artifacts = version_data.get("artifacts")
        if not isinstance(artifacts, list) or not artifacts:
            fail(f"{version_path}: 'artifacts' must be a non-empty array")
            ok = False
            continue

        for idx, artifact in enumerate(artifacts):
            artifact_path = f"{version_path}.artifacts[{idx}]"
            if not isinstance(artifact, dict):
                fail(f"{artifact_path}: artifact must be an object")
                ok = False
                continue

            for required in ("os", "arch", "url", "sha256", "fileName"):
                if required not in artifact:
                    fail(f"{artifact_path}: missing required field '{required}'")
                    ok = False

            sha = artifact.get("sha256")
            if not isinstance(sha, str) or not SHA256_RE.match(sha):
                fail(f"{artifact_path}: sha256 must be a 64-char lowercase hex string")
                ok = False

            url = artifact.get("url")
            if not isinstance(url, str) or not validate_url(url, artifact_path):
                ok = False
            else:
                if check_urls and not maybe_probe_url(url, artifact_path, timeout):
                    ok = False
                if check_sha and isinstance(sha, str) and SHA256_RE.match(sha):
                    if not maybe_verify_sha(url, sha, artifact_path, timeout):
                        ok = False

            mirrors = artifact.get("mirrors", [])
            if mirrors is not None:
                if not isinstance(mirrors, list):
                    fail(f"{artifact_path}: mirrors must be an array when present")
                    ok = False
                else:
                    for midx, mirror in enumerate(mirrors):
                        mirror_path = f"{artifact_path}.mirrors[{midx}]"
                        if not isinstance(mirror, str) or not validate_url(mirror, mirror_path):
                            ok = False
                        elif check_mirrors and not maybe_probe_url(mirror, mirror_path, timeout):
                            ok = False

    return ok


def validate_index(path: pathlib.Path, data: object, manifest_names: set[str]) -> bool:
    ok = True
    if not isinstance(data, dict):
        fail(f"{path}: index root must be an object")
        return False

    if "schemaVersion" not in data or not isinstance(data["schemaVersion"], int):
        fail(f"{path}: 'schemaVersion' must be an integer")
        ok = False

    drivers = data.get("drivers")
    if not isinstance(drivers, list):
        fail(f"{path}: 'drivers' must be an array")
        return False

    seen = set()
    for d in drivers:
        if not isinstance(d, str) or not d:
            fail(f"{path}: all 'drivers' entries must be non-empty strings")
            ok = False
            continue
        if d in seen:
            fail(f"{path}: duplicate driver '{d}' in index")
            ok = False
        seen.add(d)
        if d not in manifest_names:
            fail(f"{path}: driver '{d}' listed but {d}.json is missing")
            ok = False

    for manifest_name in manifest_names:
        if manifest_name not in seen:
            fail(f"{path}: manifest '{manifest_name}.json' exists but is not listed in drivers")
            ok = False

    return ok


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Honeydipper driver registry manifests")
    parser.add_argument("--repo", default=".", help="Path to registry repo root")
    parser.add_argument("--check-urls", action="store_true", help="Probe URLs with HTTP HEAD")
    parser.add_argument(
        "--check-mirrors",
        action="store_true",
        help="Probe mirror URLs with HTTP HEAD",
    )
    parser.add_argument("--check-sha", action="store_true", help="Download URL and verify sha256")
    parser.add_argument("--timeout", type=int, default=20, help="HTTP timeout seconds")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo = pathlib.Path(args.repo).resolve()
    index_path = repo / "index.json"

    manifest_paths = sorted(
        p
        for p in repo.glob("*.json")
        if p.name != "index.json"
    )

    if not manifest_paths:
        fail("no driver manifests found at repo root")
        return 1

    all_ok = True
    manifest_names = set()

    for mpath in manifest_paths:
        data = load_json(mpath)
        if isinstance(data, dict) and isinstance(data.get("driver"), str):
            manifest_names.add(data["driver"])
        else:
            manifest_names.add(mpath.stem)

        if not validate_manifest(
            mpath,
            data,
            args.check_urls,
            args.check_mirrors,
            args.check_sha,
            args.timeout,
        ):
            all_ok = False

    if not index_path.exists():
        fail("index.json is missing")
        all_ok = False
    else:
        idx_data = load_json(index_path)
        if not validate_index(index_path, idx_data, manifest_names):
            all_ok = False

    if all_ok:
        print("Registry validation passed")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
