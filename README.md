# BIX Backup Home Assistant Integration (`bix_backup`)

Private HACS-compatible integration for BIX Backup controller.

## Features

- Config flow + options flow
- Reads discovery + state from controller HA endpoints
- WS-first refresh (`/ws/ui`) with polling fallback
- Host/job/alert entities (job entities use friendly plan names)
- Backup metrics sensors (files processed, bytes processed, bytes added)
- Per-job and per-alert action buttons (when enabled on controller)

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
   - Controller base URL, e.g. `https://bixbackup.oneholly.com`
   - Home Assistant token from BIX UI

## Action semantics

- `Run Backup` -> `POST /api/integrations/home-assistant/actions/jobs/{job_id}/run-backup`
- `Acknowledge Alert` -> `POST /api/integrations/home-assistant/actions/alerts/{alert_id}/ack`
- `Resolve Alert` -> `POST /api/integrations/home-assistant/actions/alerts/{alert_id}/resolve`

All action requests use `Authorization: Bearer <home_assistant_token>`.
