"""
Basic tests for a processor application.

This ensures all modules are importable and that the config is valid.
"""

def test_import_handler():
    from ttn_platform_interface.handler import target
    assert target

def test_config():
    from ttn_platform_interface.app_config import TtnPlatformInterfaceConfig

    config = TtnPlatformInterfaceConfig()
    assert isinstance(config.to_dict(), dict)
