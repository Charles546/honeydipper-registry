# Honeydipper Driver Registry

This repository hosts a static driver registry for Honeydipper remote drivers.

It is designed to be served from GitHub Pages.

## Layout

- `index.json`: optional catalog of available drivers.
- `<driver-name>.json`: per-driver registry manifest consumed by Honeydipper.
- `artifacts/`: downloadable driver binaries.

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

When releasing a new driver version:

1. Build and upload a new binary under `artifacts/<driver>/<version>/...`.
2. Compute and update `sha256` in `<driver>.json`.
3. Add `versions.<version>` entry.
4. Move `channels.stable` and `latest` if needed.
5. Commit and push.

## Notes

- Current manifests include Linux amd64 artifacts.
- If you want cryptographic signatures, add `publicKey` and `signature` fields in manifest artifacts.
