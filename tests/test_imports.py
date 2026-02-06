"""
Basic tests for an application.

This ensures all modules are importable and that the config is valid.
"""

def test_import_app():
    from ttn_platform_interface.application import TtnPlatformInterfaceApplication
    assert TtnPlatformInterfaceApplication

def test_config():
    from ttn_platform_interface.app_config import TtnPlatformInterfaceConfig

    config = TtnPlatformInterfaceConfig()
    assert isinstance(config.to_dict(), dict)

def test_ui():
    from ttn_platform_interface.app_ui import TtnPlatformInterfaceUI
    assert TtnPlatformInterfaceUI

def test_state():
    from ttn_platform_interface.app_state import TtnPlatformInterfaceState
    assert TtnPlatformInterfaceState