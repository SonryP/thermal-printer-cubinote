# windows bluetooth support
#
# windows has no bluetoothctl, and no scan api without extra packages, so the
# printer is paired once in windows settings and the app offers the paired
# devices. the rfcomm socket itself needs nothing special: cpython supports
# AF_BLUETOOTH sockets on windows.

import json
import logging
import re
import subprocess
from typing import List, Tuple

logger = logging.getLogger(__name__)

# one subkey per paired classic device, named by its address in hex
_PAIRED_DEVICES_KEY = r"SYSTEM\CurrentControlSet\Services\BTHPORT\Parameters\Devices"

# classic devices enumerate as BTHENUM\DEV_<address>\...
_PNP_QUERY = (
    "Get-PnpDevice -Class Bluetooth -ErrorAction SilentlyContinue | "
    "Where-Object { $_.InstanceId -like 'BTHENUM\\DEV_*' } | "
    "Select-Object FriendlyName, InstanceId | ConvertTo-Json -Compress"
)
_PNP_ADDRESS = re.compile(r"DEV_([0-9A-F]{12})", re.IGNORECASE)


def _format_mac(hex_address: str) -> str:
    hex_address = hex_address.upper()
    return ":".join(hex_address[i:i + 2] for i in range(0, 12, 2))


def _from_registry() -> List[Tuple[str, str]]:
    import winreg

    devices = []
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, _PAIRED_DEVICES_KEY) as root:
        index = 0
        while True:
            try:
                address = winreg.EnumKey(root, index)
            except OSError:
                break
            index += 1
            if not re.fullmatch(r"[0-9a-fA-F]{12}", address):
                continue
            try:
                with winreg.OpenKey(root, address) as device:
                    raw_name, _ = winreg.QueryValueEx(device, "Name")
            except OSError:
                continue
            # stored as nul-terminated utf-8 bytes
            if isinstance(raw_name, bytes):
                name = raw_name.split(b"\x00", 1)[0].decode("utf-8", "replace")
            else:
                name = str(raw_name)
            if name:
                devices.append((_format_mac(address), name))
    return devices


def _from_pnp() -> List[Tuple[str, str]]:
    result = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", _PNP_QUERY],
        capture_output=True,
        text=True,
        timeout=15,
        # dont flash a console window from the packaged gui
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    output = result.stdout.strip()
    if result.returncode != 0 or not output:
        return []

    entries = json.loads(output)
    if isinstance(entries, dict):
        entries = [entries]

    devices = []
    for entry in entries:
        match = _PNP_ADDRESS.search(entry.get("InstanceId") or "")
        name = entry.get("FriendlyName") or ""
        if match and name:
            devices.append((_format_mac(match.group(1)), name))
    return devices


def list_paired_devices() -> List[Tuple[str, str]]:
    # returns (mac, name) for every paired classic bluetooth device
    for source in (_from_registry, _from_pnp):
        try:
            devices = source()
        except Exception as e:
            logger.info(f"Paired device lookup via {source.__name__} failed: {e}")
            continue
        if devices:
            return devices
    return []
