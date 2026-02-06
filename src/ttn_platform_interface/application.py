"""TTN Platform Interface - Doover Processor Application.

Bidirectional bridge between the Doover tag system and The Things Network (TTN).
- Uplinks: Receives TTN uplink messages via channel subscription, parses them,
  and writes the data to tags on this processor so other apps can read them.
- Downlinks: Periodically checks for pending downlink requests in tags
  and sends them to TTN via the HTTP API.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta

import aiohttp

from pydoover.cloud.processor import (
    Application,
    MessageCreateEvent,
)
from pydoover.cloud.processor.types import (
    ConnectionStatus,
    ScheduleEvent,
)

from .app_config import TtnPlatformInterfaceConfig

log = logging.getLogger(__name__)


class TtnPlatformInterface(Application):
    """TTN Platform Interface processor.

    Allows other Doover apps to publish/receive configurable information
    to/from the TTN network via the Doover tag system.

    Uplink data is stored on this processor's own tags, keyed by TTN device ID
    (using the configurable uplink tag name). Other Doover apps can read this
    processor's tags using its app_key.

    Downlink requests are read from this processor's tags (keyed by TTN device
    ID using the configurable downlink request tag name). Other Doover apps
    write to these tags to trigger downlinks.
    """

    config: TtnPlatformInterfaceConfig

    async def setup(self):
        """Initialize HTTP client session and load configuration."""
        self.http_session = aiohttp.ClientSession(
            headers={
                "User-Agent": "doover-ttn-platform-interface",
            },
            timeout=aiohttp.ClientTimeout(total=30),
        )

        # Build device mapping lookup: ttn_device_id -> doover_app_key
        self.device_map = {}
        if self.config.device_mapping and self.config.device_mapping.elements:
            for entry in self.config.device_mapping.elements:
                elems = entry.elements
                ttn_device_id = elems[0].value
                doover_app_key = elems[1].value
                if ttn_device_id and doover_app_key:
                    self.device_map[ttn_device_id] = doover_app_key

        log.info(
            "TTN Platform Interface setup complete. "
            "Device mappings: %d, API URL: %s, App ID: %s",
            len(self.device_map),
            self.config.ttn_api_url.value,
            self.config.ttn_application_id.value or "(not set)",
        )

    async def close(self):
        """Clean up HTTP client resources."""
        if self.http_session and not self.http_session.closed:
            await self.http_session.close()

    # ── Uplink Processing ──────────────────────────────────────────────

    async def on_message_create(self, event: MessageCreateEvent):
        """Process incoming TTN uplink messages from subscribed channels.

        Parses the TTN uplink JSON, maps the device to a Doover agent,
        writes parsed data to processor tags, and updates connection status.
        """
        try:
            data = event.message.data
            if isinstance(data, str):
                data = json.loads(data)

            # Extract TTN uplink fields
            end_device_ids = data.get("end_device_ids", {})
            ttn_device_id = end_device_ids.get("device_id")
            dev_eui = end_device_ids.get("dev_eui")

            uplink_message = data.get("uplink_message", {})
            f_port = uplink_message.get("f_port")
            f_cnt = uplink_message.get("f_cnt")
            frm_payload = uplink_message.get("frm_payload")
            decoded_payload = uplink_message.get("decoded_payload")
            rx_metadata = uplink_message.get("rx_metadata", [])
            received_at = uplink_message.get("received_at")

            if not ttn_device_id:
                log.warning("Uplink message missing device_id, skipping")
                return

            # Check if device is in our mapping
            doover_app_key = self.device_map.get(ttn_device_id)
            if not doover_app_key:
                log.warning(
                    "No device mapping found for TTN device '%s', skipping",
                    ttn_device_id,
                )
                if self.config.debug_enabled.value:
                    await self.set_tag(
                        "last_error",
                        f"Unmapped TTN device: {ttn_device_id}",
                    )
                return

            # Extract best RSSI and SNR from rx_metadata
            rssi = None
            snr = None
            if rx_metadata:
                best_gw = max(rx_metadata, key=lambda g: g.get("rssi", -999))
                rssi = best_gw.get("rssi")
                snr = best_gw.get("snr")

            # Build uplink tag data
            uplink_tag_name = self.config.uplink_tag_name.value or "ttn_uplink"
            now = datetime.now(timezone.utc)

            uplink_data = {
                "device_id": ttn_device_id,
                "dev_eui": dev_eui,
                "f_port": f_port,
                "f_cnt": f_cnt,
                "payload": frm_payload,
                "decoded_payload": decoded_payload,
                "rssi": rssi,
                "snr": snr,
                "timestamp": received_at or now.isoformat(),
            }

            # Write uplink data to processor's own tags, keyed by device ID
            # Other apps read this processor's tags using its app_key
            tag_key = f"{uplink_tag_name}_{ttn_device_id}"
            await self.set_tag(tag_key, uplink_data)

            # Also write a "latest uplink" summary without device-specific key
            # for quick access to most recent data
            await self.set_tag(uplink_tag_name, uplink_data)

            # Update connection status for this processor's agent
            await self.ping_connection(
                online_at=now,
                connection_status=ConnectionStatus.periodic_unknown,
                offline_at=now + timedelta(hours=1),
            )

            # Update processor-level stats
            stats = await self.get_tag("stats") or {}
            stats["uplinks_processed"] = stats.get("uplinks_processed", 0) + 1
            await self.set_tag("stats", stats)
            await self.set_tag("last_uplink_at", now.isoformat())

            # Update device mapping state with last-seen timestamp
            mapping_state = await self.get_tag("device_mapping_state") or {}
            mapping_state[ttn_device_id] = {
                "doover_app_key": doover_app_key,
                "last_seen": now.isoformat(),
                "rssi": rssi,
                "snr": snr,
            }
            await self.set_tag("device_mapping_state", mapping_state)

            log.info(
                "Processed uplink from TTN device '%s' (app_key=%s)",
                ttn_device_id,
                doover_app_key,
            )

        except Exception as e:
            log.error("Error processing uplink message: %s", e, exc_info=True)
            await self._record_error(f"Uplink processing error: {e}")

    # ── Downlink Processing ────────────────────────────────────────────

    async def on_schedule(self, event: ScheduleEvent):
        """Check for pending downlink requests and send to TTN.

        Iterates through configured device mappings, reads the downlink request
        tag from this processor's own tags, sends pending requests to TTN
        via the HTTP API, and updates status tags.

        Other Doover apps write downlink requests by setting a tag on this
        processor (e.g., ttn_downlink_request_{device_id}).
        """
        if not self.config.ttn_application_id.value:
            log.warning("TTN Application ID not configured, skipping downlink check")
            return

        if not self.config.ttn_api_key.value:
            log.warning("TTN API Key not configured, skipping downlink check")
            return

        downlink_request_tag = (
            self.config.downlink_request_tag.value or "ttn_downlink_request"
        )
        downlink_status_tag = (
            self.config.downlink_status_tag.value or "ttn_downlink_status"
        )

        downlinks_sent = 0
        errors = 0

        for ttn_device_id, doover_app_key in self.device_map.items():
            try:
                # Check for pending downlink request for this device
                request_key = f"{downlink_request_tag}_{ttn_device_id}"
                request = await self.get_tag(request_key)

                if not request:
                    continue

                # Parse downlink request fields
                f_port = request.get("f_port", 1)
                frm_payload = request.get("frm_payload")
                decoded_payload = request.get("decoded_payload")
                priority = request.get("priority", "NORMAL")
                confirmed = request.get("confirmed", False)

                if not frm_payload and not decoded_payload:
                    log.warning(
                        "Downlink request for device '%s' has no payload, skipping",
                        ttn_device_id,
                    )
                    continue

                # Build TTN downlink request body
                downlink_body = {
                    "f_port": f_port,
                    "priority": priority,
                }
                if confirmed:
                    downlink_body["confirmed"] = True

                if frm_payload:
                    downlink_body["frm_payload"] = frm_payload
                elif decoded_payload:
                    downlink_body["decoded_payload"] = decoded_payload

                payload_preview = frm_payload or json.dumps(decoded_payload)[:50]

                # Send downlink to TTN API
                success = await self._send_ttn_downlink(
                    ttn_device_id,
                    {"downlinks": [downlink_body]},
                )

                now = datetime.now(timezone.utc).isoformat()
                status_key = f"{downlink_status_tag}_{ttn_device_id}"

                if success:
                    # Clear the downlink request tag
                    await self.set_tag(request_key, None)

                    # Write success status
                    await self.set_tag(status_key, {
                        "status": "sent",
                        "sent_at": now,
                        "error": None,
                        "f_port": f_port,
                        "payload_preview": payload_preview,
                    })
                    downlinks_sent += 1

                    log.info(
                        "Sent downlink to TTN device '%s' (f_port=%d)",
                        ttn_device_id,
                        f_port,
                    )
                else:
                    errors += 1

            except Exception as e:
                log.error(
                    "Error processing downlink for device '%s': %s",
                    ttn_device_id,
                    e,
                    exc_info=True,
                )
                errors += 1
                await self._record_error(
                    f"Downlink error for {ttn_device_id}: {e}"
                )

                # Write error status for the device
                try:
                    status_key = f"{downlink_status_tag}_{ttn_device_id}"
                    await self.set_tag(status_key, {
                        "status": "error",
                        "sent_at": None,
                        "error": str(e),
                        "f_port": None,
                        "payload_preview": None,
                    })
                except Exception:
                    pass

        # Update processor-level stats
        if downlinks_sent > 0 or errors > 0:
            stats = await self.get_tag("stats") or {}
            stats["downlinks_sent"] = stats.get("downlinks_sent", 0) + downlinks_sent
            stats["errors"] = stats.get("errors", 0) + errors
            await self.set_tag("stats", stats)

            if downlinks_sent > 0:
                await self.set_tag(
                    "last_downlink_at",
                    datetime.now(timezone.utc).isoformat(),
                )

    # ── TTN API Methods ────────────────────────────────────────────────

    async def _send_ttn_downlink(
        self,
        device_id: str,
        body: dict,
        max_retries: int = 3,
    ) -> bool:
        """Send a downlink push request to the TTN Application Server API.

        Uses exponential backoff for transient failures (429, 5xx, network errors).

        Returns True if the downlink was sent successfully.
        """
        api_url = self.config.ttn_api_url.value.rstrip("/")
        app_id = self.config.ttn_application_id.value
        webhook_id = self.config.ttn_webhook_id.value or "doover"
        api_key = self.config.ttn_api_key.value

        url = (
            f"{api_url}/api/v3/as/applications/{app_id}"
            f"/webhooks/{webhook_id}/devices/{device_id}/down/push"
        )

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        last_error = None

        for attempt in range(max_retries):
            try:
                async with self.http_session.post(
                    url,
                    json=body,
                    headers=headers,
                ) as response:
                    if response.status == 200:
                        return True

                    response_text = await response.text()

                    if response.status == 401:
                        log.error(
                            "TTN API authentication failed (401). Check API key."
                        )
                        await self._record_error(
                            "TTN API authentication failed (401). Check API key."
                        )
                        return False

                    if response.status == 404:
                        log.error(
                            "TTN device or webhook not found (404) for device '%s'.",
                            device_id,
                        )
                        await self._record_error(
                            f"TTN API 404: device '{device_id}' or webhook not found."
                        )
                        return False

                    if response.status == 429:
                        wait_time = 2 ** (attempt + 1)
                        log.warning(
                            "TTN API rate limit (429), retrying in %ds...",
                            wait_time,
                        )
                        await asyncio.sleep(wait_time)
                        last_error = f"Rate limited (429): {response_text}"
                        continue

                    if response.status >= 500:
                        wait_time = 2 ** (attempt + 1)
                        log.warning(
                            "TTN API server error (%d), retrying in %ds...",
                            response.status,
                            wait_time,
                        )
                        await asyncio.sleep(wait_time)
                        last_error = (
                            f"Server error ({response.status}): {response_text}"
                        )
                        continue

                    # Other client errors - don't retry
                    log.error(
                        "TTN API error (%d) for device '%s': %s",
                        response.status,
                        device_id,
                        response_text,
                    )
                    await self._record_error(
                        f"TTN API error ({response.status}) for "
                        f"{device_id}: {response_text}"
                    )
                    return False

            except aiohttp.ClientError as e:
                wait_time = 2 ** (attempt + 1)
                log.warning(
                    "HTTP error sending downlink (attempt %d/%d): %s",
                    attempt + 1,
                    max_retries,
                    e,
                )
                last_error = str(e)
                await asyncio.sleep(wait_time)

        log.error(
            "Failed to send downlink to device '%s' after %d retries: %s",
            device_id,
            max_retries,
            last_error,
        )
        await self._record_error(
            f"Downlink failed for {device_id} after "
            f"{max_retries} retries: {last_error}"
        )
        return False

    # ── Helpers ─────────────────────────────────────────────────────────

    async def _record_error(self, message: str):
        """Record an error to the last_error tag and increment error count."""
        await self.set_tag("last_error", message)
        stats = await self.get_tag("stats") or {}
        stats["errors"] = stats.get("errors", 0) + 1
        await self.set_tag("stats", stats)
