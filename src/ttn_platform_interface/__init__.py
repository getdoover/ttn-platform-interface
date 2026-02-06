from typing import Any

from pydoover.cloud.processor import run_app

from .application import TtnPlatformInterface
from .app_config import TtnPlatformInterfaceConfig


def handler(event: dict[str, Any], context):
    """Lambda handler entry point."""
    TtnPlatformInterfaceConfig.clear_elements()
    run_app(
        TtnPlatformInterface(config=TtnPlatformInterfaceConfig()),
        event,
        context,
    )
