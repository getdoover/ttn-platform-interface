# Build Plan

## App Summary
- Name: ttn-platform-interface
- Type: processor
- Description: Allows other Doover apps to publish/receive configurable information to/from the TTN network via the Doover tag system

## External Integration
- Service: The Things Network (TTN) / The Things Stack v3
- Documentation:
  - Scheduling Downlinks: https://www.thethingsindustries.com/docs/integrations/webhooks/scheduling-downlinks/
  - Creating Webhooks: https://www.thethingsindustries.com/docs/integrations/webhooks/creating-webhooks/
  - Data Formats: https://www.thethingsindustries.com/docs/integrations/data-formats/
- Authentication: Bearer token (API key with "Write downlink application traffic" rights)

## Architecture Overview

This processor acts as a bidirectional bridge between the Doover tag system and The Things Network:

```
TTN LoRaWAN Network
       |                    ^
       | uplink             | downlink
       v                    |
  [TTN Webhook]        [TTN HTTP API]
       |                    ^
       | HTTP POST          | POST /down/push
       v                    |
  [Doover Integration]  [This Processor]
       |                    ^
       | publish channel    | read tags / on_schedule
       v                    |
  [This Processor]     [Other Doover Apps]
       |                    ^
       | set_tag            | set_tag (downlink_request)
       v                    |
  [Other Doover Apps]  [Other Doover Apps]
```

### Uplink Path (TTN -> Doover)
1. TTN sends uplink webhook to a Doover integration endpoint (separate integration app, or a channel published by an external webhook handler)
2. This processor subscribes to the channel carrying TTN uplink messages
3. On receiving an uplink message, the processor:
   - Parses the TTN uplink JSON payload (device_id, dev_eui, frm_payload, decoded_payload, rx_metadata)
   - Maps the TTN device to a Doover device using a configurable device mapping
   - Writes the uplink data to Doover tags on the mapped device so other apps can read it
   - Updates connection status for the device (ping_connection)

### Downlink Path (Doover -> TTN)
1. Other Doover apps write a downlink request to a tag (e.g., `downlink_request`) on the device
2. This processor runs on a schedule (or reacts to a channel message)
3. On each invocation, it:
   - Checks each mapped device for pending downlink requests in tags
   - If a downlink request exists, sends it to TTN via the HTTP API (`/down/push`)
   - Clears the downlink request tag after successful sending
   - Records the result in a status tag

## Data Flow

### Inputs
- **Channel subscription**: Subscribes to configurable channel(s) carrying TTN uplink messages (e.g., `ttn_uplink` or `on_external_event`)
- **Schedule trigger**: Periodic check for pending downlink requests (configurable interval)
- **Tags from other apps**: `downlink_request` tag written by other Doover apps requesting a downlink be sent to a TTN device

### Processing
1. **Uplink processing** (`on_message_create`):
   - Parse incoming TTN uplink payload
   - Extract device_id, dev_eui, f_port, frm_payload (base64), decoded_payload, rx_metadata (rssi, snr)
   - Look up Doover device mapping (TTN device_id -> Doover agent)
   - Write parsed data to tags on the target Doover device
   - Update device connection status via `ping_connection`

2. **Downlink processing** (`on_schedule`):
   - Iterate through configured device mappings
   - Check each device's `downlink_request` tag
   - If a pending request exists, call TTN API to push downlink
   - Clear the request tag and update `downlink_status` tag with result

### Outputs
- **Tags** (set on mapped Doover devices): uplink data, connection status, downlink status
- **HTTP API calls**: TTN downlink push requests
- **Tags** (set on self): device mapping state, last error, processing statistics

## Configuration Schema

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| ttn_api_url | String | yes | `https://eu1.cloud.thethings.network` | TTN cluster base URL |
| ttn_application_id | String | yes | - | TTN application ID |
| ttn_api_key | String | yes | - | TTN API key (Bearer token with downlink write rights) |
| ttn_webhook_id | String | no | `doover` | Webhook ID used for downlink API path |
| uplink_tag_name | String | no | `ttn_uplink` | Tag name to write uplink data to on devices |
| downlink_request_tag | String | no | `ttn_downlink_request` | Tag name to read downlink requests from on devices |
| downlink_status_tag | String | no | `ttn_downlink_status` | Tag name to write downlink status to on devices |
| device_mapping | Array of Object | no | `[]` | Mapping of TTN device IDs to Doover agent IDs (can also be auto-discovered) |
| debug_enabled | Boolean | no | `false` | Enable verbose debug logging to tags |

### Device Mapping Object

Each entry in `device_mapping`:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| ttn_device_id | String | yes | The device_id in TTN (e.g., `eui-0004a30b001c0530`) |
| doover_app_key | Application | yes | The Doover app key (agent) to map this device to |

### Subscriptions
- Channel pattern: Configurable via `ManySubscriptionConfig` (default subscribes to channels carrying TTN uplink data, e.g., `ttn_uplink` or `on_external_event`)
- Message types: JSON objects containing TTN uplink payloads

### Schedule
- Interval: `rate(5 minutes)` (default, configurable via `ScheduleConfig`)
- Purpose: Check for pending downlink requests and send them to TTN

## Event Handlers

| Handler | Trigger | Description |
|---------|---------|-------------|
| `setup` | Invocation start | Initialize HTTP client, load config, validate TTN credentials |
| `on_message_create` | Channel message (uplink from TTN) | Parse TTN uplink, map to Doover device, write tags, update connection status |
| `on_schedule` | Periodic (default: 5 min) | Check mapped devices for pending downlink requests, send to TTN API, update status tags |
| `close` | Invocation end | Clean up HTTP client resources |

## Tags (Output)

### Tags Set on Mapped Doover Devices

| Tag Name | Type | Description |
|----------|------|-------------|
| `ttn_uplink` (configurable) | object | Latest uplink data: `{device_id, dev_eui, f_port, payload, decoded_payload, rssi, snr, timestamp}` |
| `ttn_downlink_status` (configurable) | object | Last downlink result: `{status, sent_at, error, f_port, payload_preview}` |

### Tags Read from Mapped Doover Devices

| Tag Name | Type | Description |
|----------|------|-------------|
| `ttn_downlink_request` (configurable) | object | Downlink request: `{f_port, frm_payload, decoded_payload, priority, confirmed}` |

### Tags Set on Self (Processor)

| Tag Name | Type | Description |
|----------|------|-------------|
| `device_mapping_state` | object | Current device mapping with last-seen timestamps |
| `last_error` | string | Last error message (if any) |
| `last_uplink_at` | string | ISO timestamp of last processed uplink |
| `last_downlink_at` | string | ISO timestamp of last sent downlink |
| `stats` | object | Processing statistics: `{uplinks_processed, downlinks_sent, errors}` |

## TTN API Details

### Downlink Push Endpoint

```
POST https://{ttn_api_url}/api/v3/as/applications/{application_id}/webhooks/{webhook_id}/devices/{device_id}/down/push
```

Headers:
```
Authorization: Bearer {ttn_api_key}
Content-Type: application/json
User-Agent: doover-ttn-platform-interface
```

Request body (binary payload):
```json
{
  "downlinks": [{
    "frm_payload": "base64-encoded-bytes",
    "f_port": 1,
    "priority": "NORMAL"
  }]
}
```

Request body (decoded payload, requires TTN payload formatter):
```json
{
  "downlinks": [{
    "decoded_payload": {"bytes": [1, 2, 3]},
    "f_port": 1,
    "priority": "NORMAL"
  }]
}
```

### TTN Uplink Webhook Payload (Expected Input)

The processor expects to receive messages on its subscribed channel containing the TTN uplink JSON:

```json
{
  "end_device_ids": {
    "device_id": "eui-0004a30b001c0530",
    "application_ids": {"application_id": "my-ttn-app"},
    "dev_eui": "0004A30B001C0530",
    "dev_addr": "00BCB929"
  },
  "uplink_message": {
    "f_port": 1,
    "f_cnt": 42,
    "frm_payload": "base64data",
    "decoded_payload": {"temperature": 25.5},
    "rx_metadata": [{"rssi": -42, "snr": 4.2}],
    "settings": {
      "data_rate": {"lora": {"bandwidth": 125000, "spreading_factor": 7}},
      "frequency": "868000000"
    },
    "received_at": "2024-01-15T10:30:00Z"
  }
}
```

## Documentation Chunks

### Required Chunks
- `config-schema.md` - Configuration types and patterns (Boolean, String, Array, Object, Application, Enum)
- `cloud-handler.md` - Handler entry point, Application class, event handlers (on_message_create, on_schedule)
- `cloud-project.md` - Project setup, build.sh, deployment package, pyproject.toml
- `processor-features.md` - ManySubscriptionConfig, ScheduleConfig, ping_connection, connection status

### Recommended Chunks
- `tags-channels.md` - Tag get/set patterns, cross-app tag access via app_key, channel publishing
- `doover-config.md` - doover_config.json structure for PRO type, config_schema generation

### Discovery Keywords
subscription, schedule, rate, tag, set_tag, get_tag, app_key, connection, ping_connection, push_async, channel, publish, on_message_create, on_schedule

## Implementation Notes

### Handler Structure
- Refactor `handler.py` to use the proper `pydoover.cloud.processor.Application` base class instead of `ProcessorBase`
- Implement `__init__.py` as the Lambda entry point using `run_app()` pattern
- Use async methods for all event handlers

### HTTP Client for TTN API
- Use `aiohttp` (already in dev dependencies) for async HTTP calls to TTN downlink API
- Create the session in `setup()`, close in `close()`
- Handle HTTP errors gracefully (401 unauthorized, 404 device not found, 429 rate limit)
- Retry transient failures with exponential backoff

### External Package: `aiohttp`
- Add `aiohttp` to main dependencies in `pyproject.toml` (currently only in dev group)
- Used for async HTTP requests to TTN Application Server API

### Device Mapping Strategy
- Primary: Explicit mapping via config (ttn_device_id -> doover_app_key)
- The mapping is stored in config and can be updated by users
- Track last-seen timestamps per device in a tag for monitoring

### Idempotency
- Track processed uplink message IDs (correlation_ids or f_cnt + device_id) to avoid duplicate processing
- Clear downlink request tags atomically after successful send to prevent re-sending

### Error Handling
- Store last error in tag for visibility
- Log errors but don't re-raise for non-critical failures (e.g., one device mapping failure shouldn't stop processing others)
- Track error counts in stats tag

### Security
- TTN API key stored in Doover config (encrypted at rest by Doover platform)
- API key is used as Bearer token, never logged or stored in tags

### Build Script
- Ensure `build.sh` exists and is executable (creates `package.zip` for Lambda deployment)
- Verify `.gitignore` includes `packages_export/`, `package.zip`, `requirements.txt`
