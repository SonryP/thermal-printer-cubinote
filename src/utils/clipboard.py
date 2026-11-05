# clipboard utilities for wayland, x11 and windows

import os
import subprocess
from typing import Optional

from .runtime import IS_WINDOWS


def _tk_root():
    # tk's own clipboard is the system clipboard on windows; borrow the app's
    # root window rather than creating a stray one
    import tkinter
    return tkinter._default_root


def is_wayland() -> bool:
    if os.environ.get('XDG_SESSION_TYPE') == 'wayland':
        return True
    if os.environ.get('WAYLAND_DISPLAY'):
        return True
    return False


def _get_x11_clipboard_xclip() -> Optional[str]:
    try:
        result = subprocess.run(
            ['xclip', '-selection', 'clipboard', '-o'],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0:
            return result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def _get_x11_clipboard_xsel() -> Optional[str]:
    try:
        result = subprocess.run(
            ['xsel', '--clipboard', '--output'],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0:
            return result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def _set_x11_clipboard_xclip(text: str) -> bool:
    try:
        process = subprocess.Popen(
            ['xclip', '-selection', 'clipboard'],
            stdin=subprocess.PIPE,
            text=True
        )
        process.communicate(input=text, timeout=2)
        return process.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return False


def _set_x11_clipboard_xsel(text: str) -> bool:
    try:
        process = subprocess.Popen(
            ['xsel', '--clipboard', '--input'],
            stdin=subprocess.PIPE,
            text=True
        )
        process.communicate(input=text, timeout=2)
        return process.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return False


def clipboard_get() -> Optional[str]:
    if IS_WINDOWS:
        import tkinter
        root = _tk_root()
        if root is None:
            return None
        try:
            return root.clipboard_get()
        except tkinter.TclError:
            return None

    if is_wayland():
        try:
            result = subprocess.run(
                ['wl-paste', '--no-newline'],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0:
                return result.stdout
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return None

    # x11 - try xclip first then xsel
    content = _get_x11_clipboard_xclip()
    if content is not None:
        return content
    return _get_x11_clipboard_xsel()


def clipboard_set(text: str) -> bool:
    if IS_WINDOWS:
        import tkinter
        root = _tk_root()
        if root is None:
            return False
        try:
            root.clipboard_clear()
            root.clipboard_append(text)
            return True
        except tkinter.TclError:
            return False

    if is_wayland():
        try:
            process = subprocess.Popen(
                ['wl-copy'],
                stdin=subprocess.PIPE,
                text=True
            )
            process.communicate(input=text, timeout=2)
            return process.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return False

    # x11 - try xclip first then xsel
    if _set_x11_clipboard_xclip(text):
        return True
    return _set_x11_clipboard_xsel(text)
