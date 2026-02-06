# TTN Platform Interface

<img src="https://raw.githubusercontent.com/getdoover/ttn-platform-interface/main/assets/icon.png" alt="App Icon" style="max-width: 100px;">

**Bidirectional bridge between the Doover tag system and The Things Network (TTN), allowing other Doover apps to publish and receive configurable information to and from LoRaWAN devices.**

[![Version](https://img.shields.io/badge/version-0.1.0-blue.svg)](https://github.com/getdoover/ttn-platform-interface)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/getdoover/ttn-platform-interface/blob/main/LICENSE)

[Getting Started](#getting-started) | [Configuration](#configuration) | [Developer](https://github.com/getdoover/ttn-platform-interface/blob/main/DEVELOPMENT.md) | [Need Help?](#need-help)

<br/>

## Overview

The TTN Platform Interface is a Doover processor that bridges The Things Network (TTN) LoRaWAN platform with the Doover tag system. It enables bidirectional communication between TTN-connected LoRaWAN devices and Doover applications, so that sensor data flows seamlessly into your Doover ecosystem and commands can be sent back to devices in the field.

On the uplink side, the processor subscribes to Doover channels that receive TTN webhook payloads. When an uplink message arrives from a LoRaWAN device, the processor parses the TTN payload, extracts key fields (decoded payload, signal quality, frame counters), and writes the data to processor-level tags. Other Doover apps can then read these tags to consume sensor data without needing to understand the TTN message format.

On the downlink side, the processor runs on a configurable schedule and checks for pending downlink requests written to its tags by other Doover apps. When a request is found, the processor sends the downlink payload to the correct TTN device via the TTN Application Server HTTP API, with automatic retry logic and exponential backoff for transient failures. Status tags are updated so requesting apps can confirm delivery.

### Features

- **Uplink Processing** -- Receives TTN uplink messages via channel subscriptions, parses device IDs, payloads, signal metadata (RSSI/SNR), and writes structured data to Doover tags
- **Downlink Sending** -- Reads pending downlink requests from tags and pushes them to TTN devices via the Application Server API with configurable f_port, priority, and confirmed delivery
- **Flexible Device Mapping** -- Maps TTN device IDs to Doover app keys, allowing multiple LoRaWAN devices to be managed through a single processor instance
- **Configurable Tag Names** -- Customize the names of uplink, downlink request, and downlink status tags to avoid conflicts with other processors
- **Automatic Retry with Exponential Backoff** -- Downlink API calls retry up to 3 times with exponential backoff for rate limits (429) and server errors (5xx)
- **Per-Device Error Isolation** -- Errors for one device do not block processing of other devices; each device gets its own status tags
- **Processor-Level Statistics** -- Tracks uplinks processed, downlinks sent, error counts, and timestamps via a `stats` tag
- **Debug Mode** -- Optional verbose logging to tags for troubleshooting unmapped devices and API errors

<br/>

## Getting Started

### Prerequisites

1. **A Things Network (TTN) Account** -- You need an active TTN v3 application at [The Things Network Console](https://console.cloud.thethings.network/)
2. **TTN API Key** -- Generate an API key in your TTN application with at least **"Write downlink application traffic"** rights
3. **TTN Webhook** -- Configure a webhook in your TTN application that forwards uplink messages to a Doover channel
4. **Doover Platform Account** -- Access to the Doover platform with permissions to create processors and configure channels

### Installation

1. Add the **TTN Platform Interface** processor to your Doover deployment via the Doover platform
2. Configure the required settings (TTN Application ID, API Key, device mappings) through the processor's configuration panel
3. Set up a TTN webhook in The Things Network Console that posts uplink messages to the Doover channel your processor subscribes to

### Quick Start

1. Create a new instance of the TTN Platform Interface processor in Doover
2. Enter your **TTN Application ID** and **TTN API Key**
3. Add at least one **Device Mapping** entry, pairing a TTN device ID (e.g., `eui-0004a30b001c0530`) with a Doover app key
4. Configure the **Subscription** to the Doover channel that receives TTN webhook payloads
5. Set a **Schedule** for how often the processor checks for pending downlink requests
6. Deploy -- uplink data will appear on the processor's tags as soon as TTN webhook messages arrive

<br/>

## Configuration

| Setting | Description | Default |
|---------|-------------|---------|
| **Subscription** | A list of Doover channels to subscribe to for receiving TTN uplink messages | *Required* |
| **Schedule** | Cron-style schedule that controls how often the processor checks for pending downlink requests | *Required* |
| **TTN Cluster URL** | Base URL of your TTN cluster (e.g., `https://eu1.cloud.thethings.network`) | `https://eu1.cloud.thethings.network` |
| **TTN Application ID** | Your application ID in The Things Network Console | *Required* |
| **TTN API Key** | API key with "Write downlink application traffic" rights (used as Bearer token) | *Required* |
| **TTN Webhook ID** | The webhook ID used in the TTN downlink API path | `doover` |
| **Uplink Tag Name** | Tag name prefix for writing uplink data on the processor | `ttn_uplink` |
| **Downlink Request Tag** | Tag name prefix for reading downlink requests from the processor | `ttn_downlink_request` |
| **Downlink Status Tag** | Tag name prefix for writing downlink delivery status on the processor | `ttn_downlink_status` |
| **Device Mapping** | Array of TTN device ID to Doover app key pairs | *Required* |
| **Debug Enabled** | Enable verbose debug logging to tags (e.g., logs unmapped device warnings) | `false` |

### Device Mapping

Each entry in the Device Mapping array requires:

| Field | Description |
|-------|-------------|
| **TTN Device ID** | The `device_id` as shown in TTN (e.g., `eui-0004a30b001c0530`) |
| **Doover App Key** | The Doover app key (agent) that this TTN device maps to |

### Example Configuration

```json
{
  "dv_proc_subscriptions": ["ttn-webhook-channel"],
  "dv_proc_schedules": "*/5 * * * *",
  "ttn_cluster_url": "https://eu1.cloud.thethings.network",
  "ttn_application_id": "my-ttn-app",
  "ttn_api_key": "NNSXS.XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
  "ttn_webhook_id": "doover",
  "uplink_tag_name": "ttn_uplink",
  "downlink_request_tag": "ttn_downlink_request",
  "downlink_status_tag": "ttn_downlink_status",
  "device_mapping": [
    {
      "ttn_device_id": "eui-0004a30b001c0530",
      "doover_app_key": "my-doover-agent-key"
    },
    {
      "ttn_device_id": "eui-00a1b2c3d4e5f678",
      "doover_app_key": "another-doover-agent-key"
    }
  ],
  "debug_enabled": false
}
```

<br/>

## Tags

This processor exposes the following tags:

| Tag | Description |
|-----|-------------|
| **`{uplink_tag_name}`** | Latest uplink data from any mapped device (contains `device_id`, `dev_eui`, `f_port`, `f_cnt`, `payload`, `decoded_payload`, `rssi`, `snr`, `timestamp`) |
| **`{uplink_tag_name}_{device_id}`** | Uplink data for a specific TTN device, keyed by device ID (same structure as above) |
| **`{downlink_request_tag}_{device_id}`** | Pending downlink request for a specific device. Other apps write to this tag to trigger a downlink. Expected fields: `f_port`, `frm_payload` or `decoded_payload`, `priority`, `confirmed` |
| **`{downlink_status_tag}_{device_id}`** | Downlink delivery status for a specific device (`status`, `sent_at`, `error`, `f_port`, `payload_preview`) |
| **`stats`** | Processor-level statistics: `uplinks_processed`, `downlinks_sent`, `errors` |
| **`last_uplink_at`** | ISO 8601 timestamp of the most recent uplink processed |
| **`last_downlink_at`** | ISO 8601 timestamp of the most recent downlink sent |
| **`last_error`** | Description of the most recent error (API failures, unmapped devices, etc.) |
| **`device_mapping_state`** | Live state of device mappings including `last_seen`, `rssi`, and `snr` per device |

### Uplink Tag Data Structure

```json
{
  "device_id": "eui-0004a30b001c0530",
  "dev_eui": "0004A30B001C0530",
  "f_port": 1,
  "f_cnt": 1234,
  "payload": "SGVsbG8=",
  "decoded_payload": { "temperature": 22.5, "humidity": 65 },
  "rssi": -95,
  "snr": 7.5,
  "timestamp": "2026-02-06T12:00:00Z"
}
```

### Downlink Request Tag Structure

To send a downlink to a TTN device, write data to the `{downlink_request_tag}_{device_id}` tag on this processor:

```json
{
  "f_port": 1,
  "frm_payload": "AQID",
  "priority": "NORMAL",
  "confirmed": false
}
```

Or use a decoded payload instead of raw bytes:

```json
{
  "f_port": 1,
  "decoded_payload": { "led": "on" },
  "priority": "HIGH",
  "confirmed": true
}
```

<br/>

## How It Works

1. **Channel Subscription** -- The processor subscribes to one or more Doover channels. A TTN webhook is configured to forward uplink messages from your TTN application to these channels.
2. **Uplink Parsing** -- When a message arrives (`on_message_create`), the processor parses the TTN uplink JSON, extracts the device ID, payload, signal metadata (RSSI, SNR), and frame counters.
3. **Device Mapping Lookup** -- The processor looks up the TTN device ID in its configured device mapping table. Unmapped devices are logged and skipped.
4. **Tag Writing (Uplinks)** -- Parsed uplink data is written to processor-level tags: a device-specific tag (`ttn_uplink_{device_id}`) and a latest-uplink summary tag (`ttn_uplink`). Connection status and statistics are updated.
5. **Scheduled Downlink Check** -- On a configurable schedule (`on_schedule`), the processor iterates through all mapped devices and checks for pending downlink requests in their `ttn_downlink_request_{device_id}` tags.
6. **Downlink Push to TTN** -- For each pending request, the processor builds a TTN API-compliant payload and sends it via HTTP POST to the TTN Application Server downlink push endpoint, with up to 3 retries using exponential backoff. On success, the request tag is cleared and a status tag is written.

<br/>

## Integrations

This processor works with:

- **The Things Network (TTN) v3** -- Connects to the TTN Application Server API for sending downlinks and receives uplinks via TTN webhooks
- **Doover Tag System** -- Reads and writes tags on the processor agent, enabling other Doover apps to consume uplink data and submit downlink requests
- **Doover Channel System** -- Subscribes to channels to receive real-time TTN webhook payloads forwarded by the platform
- **Any LoRaWAN Device** -- Works with any LoRaWAN device registered in your TTN application, regardless of manufacturer or sensor type

<br/>

## Need Help?

- Email: support@doover.com
- [Doover Documentation](https://docs.doover.com)
- [App Developer Documentation](https://github.com/getdoover/ttn-platform-interface/blob/main/DEVELOPMENT.md)

<br/>

## Version History

### v0.1.0 (Current)
- Initial release
- Bidirectional TTN bridge (uplinks and downlinks)
- Configurable device mapping (TTN device ID to Doover app key)
- TTN Application Server API integration with retry and exponential backoff
- Per-device uplink, downlink request, and downlink status tags
- Processor-level statistics and error tracking
- Debug mode for verbose tag-based logging

<br/>

## License

This app is licensed under the [Apache License 2.0](https://github.com/getdoover/ttn-platform-interface/blob/main/LICENSE).
