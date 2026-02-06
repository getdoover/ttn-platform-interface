from pydoover.docker import run_app

from .application import TtnPlatformInterfaceApplication
from .app_config import TtnPlatformInterfaceConfig

def main():
    """
    Run the application.
    """
    run_app(TtnPlatformInterfaceApplication(config=TtnPlatformInterfaceConfig()))
