# Honeydipper Driver Registry

This repository hosts a static driver registry for Honeydipper remote drivers.

It is designed to be served from GitHub Pages.

## Layout

- `index.json`: optional catalog of available drivers.
- `<driver-name>.json`: per-driver registry manifest consumed by Honeydipper.
- `artifacts/`: optional mirror binaries for resilience/fallback operations.
- `.github/workflows/validate-registry.yml`: CI validation for manifests.
- `.github/workflows/release-driver.yml`: reusable workflow for driver repos.

## Included Drivers

- `hd-driver-podman`
- `hd-driver-auth-github`

## GitHub Pages URL

After publishing this repository as GitHub Pages from the default branch root,
use this registry base URL in Honeydipper:

`https://charles546.github.io/honeydipper-registry`

Honeydipper resolves manifests as:

`<registryURL>/<driverName>.json`

Example:

`https://charles546.github.io/honeydipper-registry/hd-driver-podman.json`

## Honeydipper Configuration Example

```yaml
---
drivers:
  daemon:
    registries:
      charles-gh-pages:
        baseURL: https://charles546.github.io/honeydipper-registry

    drivers:
      hd-driver-podman:
        name: hd-driver-podman
        type: remote
        handlerData:
          registry: charles-gh-pages
          channel: stable

      hd-driver-auth-github:
        name: hd-driver-auth-github
        type: remote
        handlerData:
          registry: charles-gh-pages
          channel: stable
```

## Release Update Workflow

Preferred flow is metadata-first:

1. Driver repositories publish GitHub Release assets.
2. Registry manifests reference release asset URLs + `sha256`.
3. Optional mirror URLs can point to `artifacts/` in this repo.

See detailed process in [docs/release-process.md](./docs/release-process.md).

Manual fallback when automation is unavailable:

1. Build and upload a new binary in the driver repository release.
2. Compute and update `sha256` in `<driver>.json`.
3. Add `versions.<version>` entry.
4. Move `channels.stable` and `latest` if needed.
5. Commit and push.

## Notes

- Current manifests include Linux amd64 artifacts.
- If you want cryptographic signatures, add `publicKey` and `signature` fields in manifest artifacts.
