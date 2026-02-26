# BIX Backup Home Assistant Integration (`bix_backup`)

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/)
[![Validate](https://github.com/oneholly/bix-backup-ha/actions/workflows/validate.yml/badge.svg)](https://github.com/oneholly/bix-backup-ha/actions/workflows/validate.yml)
[![Hassfest](https://github.com/oneholly/bix-backup-ha/actions/workflows/hassfest.yml/badge.svg)](https://github.com/oneholly/bix-backup-ha/actions/workflows/hassfest.yml)
[![Release](https://img.shields.io/github/v/release/oneholly/bix-backup-ha?display_name=tag)](https://github.com/oneholly/bix-backup-ha/releases)

Private HACS-compatible integration for the BIX Backup controller.

[![Open your Home Assistant instance and open this repository inside Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=oneholly&repository=bix-backup-ha)

## Features

- Config flow + options flow
- Reads discovery + state from controller Home Assistant endpoints
- WebSocket-first refresh (`/ws/ui`) with polling fallback
- Host/job/alert entities (job entities use friendly plan names)
- Backup metrics sensors (files processed, bytes processed, bytes added)
- Per-job and per-alert action buttons (when enabled on controller)

## HACS and versioning notes

- Minimum supported Home Assistant version is `2026.2.0`.
- Required: keep `custom_components/bix_backup/manifest.json` `version` up to date.
- This repo auto-creates a GitHub release/tag (`v<manifest version>`) when `manifest.json` version changes on `main`.
- Recommended: publish GitHub releases (for example `v0.1.0`) that match the manifest version.
- If you want to submit this to the HACS default repository later, release-based installs and Home Assistant Brands assets become required.

## Required controller setup

1. Configure in BIX UI: `Settings -> Home Assistant`
2. Enable integration
3. Set Home Assistant token
4. Optional for actions: enable write actions

## Install with HACS (private repo)

1. HACS -> Integrations -> Custom repositories
2. Add your private repo URL
3. Category: `Integration`
4. Install `BIX Backup`
5. Restart Home Assistant

## Add integration

1. Settings -> Devices & Services -> Add Integration
2. Search `BIX Backup`
3. Enter:
   - Controller base URL, for example `https://bixbackup.oneholly.com`
   - Home Assistant token from BIX UI

## Action semantics

- `Run Backup` -> `POST /api/integrations/home-assistant/actions/jobs/{job_id}/run-backup`
- `Acknowledge Alert` -> `POST /api/integrations/home-assistant/actions/alerts/{alert_id}/ack`
- `Resolve Alert` -> `POST /api/integrations/home-assistant/actions/alerts/{alert_id}/resolve`

All action requests use `Authorization: Bearer <home_assistant_token>`.
