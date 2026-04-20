# Driver Release And Registry Update Process

This registry uses a metadata-first model:

1. Driver binaries are published from each driver repository GitHub Release.
2. Registry manifests hold URL, sha256, and channel metadata.
3. Optional mirror URLs can point to this registry's GitHub Pages artifacts.

## Prerequisites

In each driver repository, add repository secret:

- `REGISTRY_REPO_TOKEN`: a PAT with `repo` scope and access to `Charles546/honeydipper-registry`.

## Recommended Driver Workflow

1. Push a version tag (for example `v0.2.0`).
2. Driver release workflow builds binary and creates/updates GitHub Release asset.
3. Workflow computes SHA256 and opens a PR in `honeydipper-registry` updating manifest.
4. Registry CI validates manifest structure and artifact URL availability.
5. Merge PR to publish registry metadata via GitHub Pages.

## Reusable Workflow

This repository provides reusable workflow:

- `.github/workflows/release-driver.yml`

Driver repositories can call it with `workflow_call` and pass:

- `driver_name`
- `binary_name`
- `go_build_path`
- `release_tag`
- `manifest_file`

Optional:

- `channel` (default `stable`)
- `mirror_url`

## Manual Fallback Procedure

If automation fails:

1. Build and release artifact manually in driver repository.
2. Compute SHA256.
3. Update `<driver>.json` in this registry.
4. Run `python3 tools/validate_registry.py --repo . --check-urls`.
5. Commit and merge.
