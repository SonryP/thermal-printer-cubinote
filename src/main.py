#!/usr/bin/env python3
# ------------------------------------------------------------------------------
# Thermal Printer
# Credits and Acknowledgments
#
# This project builds upon the incredible reverse engineering work of the
# maker and hacker community who cracked the Core Innovation CTP-500
# Bluetooth thermal printer protocol.
#
# ORIGINAL RESEARCH AND DEVELOPMENT
#
#   Mel (ThirtyThreeDown Studio)
#     Primary developer of the original CTP500PrinterApp
#     Bluetooth protocol analysis and GUI implementation
#     https://thirtythreedown.com
#     https://github.com/thirtythreedown/CTP500PrinterApp
#
#   voidsshadows
#     Creator of CorePrint print server
#     Stripped-down Python implementation that formed the foundation
#     https://github.com/voidsshadows/CorePrint-print-server
#
# SECKC CONTRIBUTORS
# Kansas City's Hacker Hive - https://seckc.org
#
#   bitflip
#     Shared critical code resources and collaboration
#
#   Tsathoggualware
#     Research and development support
#
#   Reid
#     Research and development support
#
# COMMUNITY CONTRIBUTORS
#
#   onezeronull, MaikelChan, rbaron, WerWolv
#     Prior thermal printer research and documentation
#
#   Nathaniel (Doodad/Dither Me This)
#     Dithering algorithm inspiration
#
#   Hacking Modern Life (YouTube)
#     Bluetooth reverse engineering tutorials
#
# SPECIAL THANKS
#
# "To all the mad lasses and lads in the maker community whose thermal
# printer research since 2014 made this possible."
#   — Mel, ThirtyThreeDown Studio
#
# ------------------------------------------------------------------------------
# License: This project is open source.
# Original CTP500PrinterApp by ThirtyThreeDown Studio.
# CorePrint by voidsshadows (AGPL-3.0).
# ------------------------------------------------------------------------------
#
# Usage:
#     python -m src.main
#     or
#     python src/main.py
# ------------------------------------------------------------------------------

import logging
import os
import sys
from pathlib import Path

# Ensure src directory is in path for imports
src_dir = Path(__file__).parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir.parent))

from src.utils.runtime import IS_FROZEN, LOG_FILENAME, app_dir

# set by the windows build job: start the packaged app, then quit
SMOKE_TEST = os.environ.get("THERMAL_PRINTER_SMOKE_TEST") == "1"


def _prepare_frozen_runtime() -> None:
    # a packaged exe runs from a temporary folder and has no console. work from
    # the exe's folder so the gallery's relative paths land beside it, and log
    # to a file there instead of the missing stdout
    os.chdir(app_dir())
    if sys.stdout is None:
        log = open(app_dir() / LOG_FILENAME, "a", buffering=1, encoding="utf-8")
        sys.stdout = sys.stderr = log
        logging.basicConfig(
            level=logging.INFO,
            stream=log,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )


def _report_startup_error(message: str) -> None:
    print(message)
    if IS_FROZEN and not SMOKE_TEST:
        # nobody sees stdout in a packaged app, so say it in a dialog
        try:
            from tkinter import messagebox
            messagebox.showerror("Thermal Printer", message)
        except Exception:
            pass


def main() -> None:
    if IS_FROZEN:
        _prepare_frozen_runtime()

    try:
        from src.gui.app import PrinterApp
        app = PrinterApp()
        if SMOKE_TEST:
            app.after(3000, app.destroy)
        app.mainloop()
    except ImportError as e:
        _report_startup_error(
            f"Import error: {e}\n\n"
            "Make sure all dependencies are installed:\n"
            "  pip install customtkinter pillow pyyaml numpy"
        )
        sys.exit(1)
    except Exception as e:
        _report_startup_error(f"Error starting application: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
