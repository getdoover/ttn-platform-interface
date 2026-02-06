from pathlib import Path

from pydoover import config
from pydoover.cloud.processor import ManySubscriptionConfig, ScheduleConfig

# Fix pydoover doover-2 branch bug: Application._type should be "string"
# (it inherits "unknown" from ConfigElement base class)
if config.Application._type == "unknown":
    config.Application._type = "string"


class TtnPlatformInterfaceConfig(config.Schema):
    def __init__(self):
        # Channel subscriptions (receives TTN uplink messages)
        self.subscription = ManySubscriptionConfig()

        # Schedule for periodic downlink processing
        self.schedule = ScheduleConfig()

        # TTN API connection settings
        self.ttn_api_url = config.String(
            "TTN Cluster URL",
            description="TTN cluster base URL (e.g., https://eu1.cloud.thethings.network)",
            default="https://eu1.cloud.thethings.network",
        )
        self.ttn_application_id = config.String(
            "TTN Application ID",
            description="The TTN application ID",
        )
        self.ttn_api_key = config.String(
            "TTN API Key",
            description="TTN API key (Bearer token with 'Write downlink application traffic' rights)",
        )
        self.ttn_webhook_id = config.String(
            "TTN Webhook ID",
            description="Webhook ID used for the downlink API path",
            default="doover",
        )

        # Tag name configuration
        self.uplink_tag_name = config.String(
            "Uplink Tag Name",
            description="Tag name to write uplink data to on mapped devices",
            default="ttn_uplink",
        )
        self.downlink_request_tag = config.String(
            "Downlink Request Tag",
            description="Tag name to read downlink requests from on mapped devices",
            default="ttn_downlink_request",
        )
        self.downlink_status_tag = config.String(
            "Downlink Status Tag",
            description="Tag name to write downlink status to on mapped devices",
            default="ttn_downlink_status",
        )

        # Device mapping: TTN device IDs to Doover app keys
        self.device_mapping = config.Array(
            "Device Mapping",
            element=config.Object("Device Map Entry"),
        )
        self.device_mapping.element.add_elements(
            config.String(
                "TTN Device ID",
                description="The device_id in TTN (e.g., eui-0004a30b001c0530)",
            ),
            config.Application(
                "Doover App Key",
                description="The Doover app key (agent) to map this TTN device to",
            ),
        )

        # Debug mode
        self.debug_enabled = config.Boolean(
            "Debug Enabled",
            description="Enable verbose debug logging to tags",
            default=False,
        )


def export():
    TtnPlatformInterfaceConfig().export(
        Path(__file__).parents[2] / "doover_config.json",
        "ttn_platform_interface",
    )


if __name__ == "__main__":
    export()
