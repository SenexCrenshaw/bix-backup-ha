# BIX Backup Home Assistant Integration (`bix_backup`)

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/)
[![Validate](https://github.com/SenexCrenshaw/bix-backup-ha/actions/workflows/validate.yml/badge.svg)](https://github.com/SenexCrenshaw/bix-backup-ha/actions/workflows/validate.yml)
[![Hassfest](https://github.com/SenexCrenshaw/bix-backup-ha/actions/workflows/hassfest.yml/badge.svg)](https://github.com/SenexCrenshaw/bix-backup-ha/actions/workflows/hassfest.yml)
[![Release](https://img.shields.io/github/v/release/SenexCrenshaw/bix-backup-ha?display_name=tag)](https://github.com/SenexCrenshaw/bix-backup-ha/releases)

Private HACS-compatible integration for the BIX Backup controller.

[![Open your Home Assistant instance and open this repository inside Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=SenexCrenshaw&repository=bix-backup-ha)

## Features

- Config flow + options flow
- Uses only the dedicated controller Home Assistant contract:
  - `GET /api/integrations/home-assistant/discovery`
  - `GET /api/integrations/home-assistant/state`
  - `POST /api/integrations/home-assistant/actions/...`
  - `/ws/ui`
- Treats discovery as the schema/capability source and state as the live runtime source
- WebSocket-first refresh (`/ws/ui`) with discovery-driven polling fallback
- Host/job/alert entities track live inventory, so new jobs and open alerts appear without reloading the integration
- Job entities use `job_id`, `job_name`, and `host_id`; no repo-centric fields are expected
- Backup metrics sensors (files processed, bytes processed, bytes added)
- Per-job and per-alert action buttons follow controller capabilities and integration options
- Adds a `BIX Backup` sidebar panel that renders a dynamic HA-native overview from BIX entities and action buttons

## HACS and versioning notes

- Target Home Assistant version is `2026.2.0+`.
- Required: keep `custom_components/bix_backup/manifest.json` `version` up to date.
- This repo auto-creates a GitHub release/tag (`v<manifest version>`) when `manifest.json` version changes on `main`.
- Recommended: publish GitHub releases (for example `v0.1.0`) that match the manifest version.
- If you want to submit this to the HACS default repository later, release-based installs and Home Assistant Brands assets become required.
- Canonical cross-repo release checklist: `https://github.com/SenexCrenshaw/bix-backup/blob/main/docs/release-checklist.md`

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

## Local development

1. Create a virtual environment:
   `python3 -m venv .venv`
2. Activate it:
   `source .venv/bin/activate`
3. Install test dependencies:
   `python -m pip install -r requirements-test.txt`
4. Run the test suite:
   `python -m pytest`

If you prefer a shorter command after activating the venv, run:
`make test`

## Add integration

1. Settings -> Devices & Services -> Add Integration
2. Search `BIX Backup`
3. Enter:
   - Controller base URL, for example `https://bixbackup.example.com`
   - Home Assistant token from BIX UI

## V1 operator path

1. Install or update from HACS
2. Restart Home Assistant
3. Add the `BIX Backup` integration from Devices & Services
4. Verify entities appear and the `BIX Backup` sidebar panel loads
5. Import the backup-finished blueprint and save one live automation
6. Test one job action and, if enabled, one alert action
7. Use the canonical cross-repo release checklist before publishing both repos:
   `https://github.com/SenexCrenshaw/bix-backup/blob/main/docs/release-checklist.md`

## Action semantics

- `Run Backup` -> `POST /api/integrations/home-assistant/actions/jobs/{job_id}/run-backup`
- `Acknowledge Alert` -> `POST /api/integrations/home-assistant/actions/alerts/{alert_id}/ack`
- `Resolve Alert` -> `POST /api/integrations/home-assistant/actions/alerts/{alert_id}/resolve`

All action requests use `Authorization: Bearer <home_assistant_token>`.

## Runtime behavior

- Discovery `transport.supported_events` controls which `/ws/ui` events trigger refreshes.
- Discovery `transport.poll_fallback_seconds` seeds the polling fallback interval unless you override it in integration options.
- Discovery `capabilities.job_actions` and `capabilities.alert_actions` gate which action buttons are created.
- Discovery `entity_catalog` controls which host/job/report fields become entities.
- `enable_job_entities` controls job sensors and binary sensors.
- `enable_host_entities` controls host sensors and binary sensors.
- `enable_action_buttons` controls job run-backup buttons.
- `enable_alert_entities` controls per-alert acknowledge and resolve buttons.
- Report summary sensors expose the latest archived controller report metadata; report generation and artifact downloads remain controller-only.

## Automation example

- A WhatsApp notification template for `backup finished` events is included at [examples/automation_whatsapp_backup_finished.yaml](/home/dbakker/git/bix-backup-ha/examples/automation_whatsapp_backup_finished.yaml).
- The example file is a copy-paste starting point if you want to hand-edit entity ids.
- A reusable automation blueprint is included at [blueprints/automation/bix_backup/whatsapp_backup_finished.yaml](/home/dbakker/git/bix-backup-ha/blueprints/automation/bix_backup/whatsapp_backup_finished.yaml).
- The blueprint only needs the job's `last_execution_time` sensor plus a WhatsApp number; it derives the matching BIX status and metric sensors automatically.
- Direct Home Assistant blueprint import URL:
  `https://raw.githubusercontent.com/senexcrenshaw/bix-backup-ha/main/blueprints/automation/bix_backup/whatsapp_backup_finished.yaml`

## Release order

1. Publish `bix-backup` when controller, UI, or API changes are ready.
2. Validate this HA integration against the tagged controller build if either repo changed in HA-facing ways.
3. Publish `bix-backup-ha` only after that compatibility check passes.
