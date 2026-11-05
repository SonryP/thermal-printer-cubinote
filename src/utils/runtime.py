# where the app is running: packaged exe or source checkout, and on which os

import sys
from pathlib import Path

IS_WINDOWS = sys.platform == "win32"

# pyinstaller sets sys.frozen. the bundled code then lives in a temporary
# folder that is wiped when the exe exits, so anything the app writes has to
# go next to the exe instead
IS_FROZEN = bool(getattr(sys, "frozen", False))

LOG_FILENAME = "thermal-printer.log"


def app_dir() -> Path:
    # writable home for config.yaml, the gallery and the log
    if IS_FROZEN:
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent.parent
