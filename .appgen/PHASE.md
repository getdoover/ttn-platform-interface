# AppGen State

## Current Phase
Phase 6 - Document

## Status
completed

## App Details
- **Name:** ttn-platform-interface
- **Description:** Allows other Doover apps to publish/receive configurable information to/from the TTN network via the Doover tag system
- **App Type:** processor
- **Has UI:** false
- **Container Registry:** ghcr.io/getdoover
- **Target Directory:** /home/sid/ttn-platform-interface
- **GitHub Repo:** getdoover/ttn-platform-interface
- **Repo Visibility:** public
- **GitHub URL:** https://github.com/getdoover/ttn-platform-interface
- **Icon URL:** https://raw.githubusercontent.com/getdoover/ttn-platform-interface/main/assets/icon.png

## Completed Phases
- [x] Phase 1: Creation - 2026-02-06T06:02:25Z
- [x] Phase 2: Processor Config - 2026-02-06T06:07:00Z
  - UI removed (has_ui: false): app_ui.py deleted, application.py cleaned
  - Build workflow removed: build-image.yml, Dockerfile, .dockerignore deleted
  - Simulators directory removed (Docker template boilerplate)
  - App state module removed (app_state.py, Docker template boilerplate)
  - Handler module created for processor pattern (handler.py with target class)
  - Icon validated, converted from SVG to 256x256 PNG, stored in assets/icon.png
  - doover_config.json restructured for processor type (type: PRO, lambda_config)
  - pyproject.toml updated (removed doover-app-run script, transitions dependency)
- [x] Phase 3: Processor Plan - 2026-02-06
  - TTN (The Things Network) v3 API researched for downlink push and uplink webhook formats
  - Bidirectional data flow designed: uplinks via channel subscription, downlinks via scheduled TTN API calls
  - Configuration schema designed: TTN API credentials, device mapping, tag name configuration
  - Event handlers planned: on_message_create (uplink processing), on_schedule (downlink sending)
  - Tags design: ttn_uplink, ttn_downlink_request, ttn_downlink_status per device, plus processor-level stats
  - External dependency identified: aiohttp for async HTTP calls to TTN API
  - PLAN.md created with complete implementation details
- [x] Phase 4: Processor Build - 2026-02-06
  - Application class (TtnPlatformInterface) created with full bidirectional TTN bridge logic
  - Lambda handler entry point (__init__.py) created using run_app() pattern
  - Config schema (app_config.py) with TTN credentials, device mapping, tag names, subscriptions, schedule
  - Event handlers: on_message_create (uplink parsing/tag writes), on_schedule (downlink sending)
  - TTN API integration: downlink push via aiohttp with exponential backoff retry
  - Error handling: per-device error isolation, stats tracking, last_error tag
  - pydoover upgraded to 0.4.18 (doover-2 branch) for Application/run_app support
  - aiohttp added as main dependency for async HTTP calls
  - build.sh created for Lambda deployment packaging
  - doover_config.json regenerated with full config_schema
  - Old handler.py stub removed (replaced by proper Application class)
- [x] Phase 5: Processor Check - 2026-02-06
  - Dependencies (uv sync): PASS - resolved 23 packages, cleaned leftover six/transitions
  - Imports (handler): PASS - `from ttn_platform_interface import handler` succeeds
  - Config Schema (doover config-schema export): PASS (after fix)
    - Fixed: pydoover doover-2 branch bug where config.Application._type="unknown" (invalid JSON Schema type)
    - Applied monkey-patch in app_config.py to set Application._type="string"
    - doover_config.json regenerated with valid schema
  - File Structure: PASS
    - src/ttn_platform_interface/__init__.py (Lambda handler entry point)
    - src/ttn_platform_interface/application.py (Application class)
    - src/ttn_platform_interface/app_config.py (Configuration schema)
    - build.sh (Lambda packaging script)
    - doover_config.json (Doover configuration)
  - doover_config.json: PASS
    - type: "PRO" (correct for processor)
    - handler: "src.ttn_platform_interface.handler" (correct Lambda handler path)
    - lambda_config: Runtime python3.13, Timeout 300, MemorySize 128
    - config_schema: valid JSON Schema with all required fields

- [x] Phase 6: Document - 2026-02-06
  - README.md generated with all required sections
  - 11 configuration items documented (Subscription, Schedule, TTN Cluster URL, TTN Application ID, TTN API Key, TTN Webhook ID, Uplink Tag Name, Downlink Request Tag, Downlink Status Tag, Device Mapping, Debug Enabled)
  - 9 tags documented (uplink, uplink per-device, downlink request, downlink status, stats, last_uplink_at, last_downlink_at, last_error, device_mapping_state)
  - Sections: Overview, Features, Getting Started, Configuration, Tags, How It Works, Integrations, Need Help, Version History, License

## References
- **Has References:** false

## User Decisions
- App name: ttn-platform-interface
- Description: Allows other Doover apps to publish/receive configurable information to/from the TTN network via the Doover tag system
- GitHub repo: getdoover/ttn-platform-interface
- App type: processor
- Has UI: false
- Has references: false
- Icon URL: https://upload.wikimedia.org/wikipedia/commons/b/b4/The_Things_Network_logo.svg

## Next Action
Phase 6 complete. README.md generated. Ready for deployment.
