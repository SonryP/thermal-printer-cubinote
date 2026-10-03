# cubinote / memobird family protocol
#
# The Cubinote prints the same escpos raster as the CTP-500, but none of its
# escpos commands drive the auto-cutter - only the vendor's JSON note jobs do,
# with the firmware cutting once a note finishes. So a print goes out as one
# continuous raster and is closed with a tiny JSON note (a single blank row)
# whose only purpose is that cut.
#
# Sending the image itself as a JSON note works but prints worse: the firmware
# dropped a 20KB package while 8KB ones printed, and splitting a tall image
# across packages leaves a white line at every join.
#
# A note travels over the same RFCOMM link in a small binary frame:
#
#     0x12 0x50 | uint16-LE payload length | JSON (utf-8)
#
# and is answered in the same framing with an ack whose "result" is 1 when
# accepted. Acks are best effort - the vendor app never waits for them.
#
# Rules the firmware enforces on notes:
# - it silently skips a printID it has already printed, so every note needs a
#   fresh one; the vendor app uses wall-clock milliseconds truncated to 32 bits
# - bitmaps are base64 1-bpp BMP files where 0 = ink, rows stored top-down,
#   with biSizeImage and the resolution fields left at zero as the vendor's
#   own encoder writes them
# - the JSON goes on a single line; the parser is picky about layout
#
# Protocol recovered from an HCI capture and logcat of the vendor app
# (cn.memobird.cubinote 1.3.1), cross-checked against ha-memobird-local.

import base64
import io
import json
import struct
import time
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image, ImageOps

from ..config.defaults import (
    CUBINOTE_PRINTER_WIDTH,
    CUBINOTE_FRAME_MAGIC,
    CUBINOTE_COMMAND_PRINT,
)


class CubinoteProtocol:
    PRINTER_WIDTH = CUBINOTE_PRINTER_WIDTH

    FRAME_MAGIC = CUBINOTE_FRAME_MAGIC
    COMMAND_PRINT = CUBINOTE_COMMAND_PRINT

    TYPE_IMAGE = 5

    # bitmap info header fields the vendor encoder leaves at zero:
    # biSizeImage, biXPelsPerMeter, biYPelsPerMeter
    _BMP_ZEROED_OFFSETS = (34, 38, 42)

    _last_print_id = 0

    @classmethod
    def frame(cls, payload: bytes) -> bytes:
        return cls.FRAME_MAGIC + struct.pack("<H", len(payload)) + payload

    @classmethod
    def split_frame(cls, data: bytes) -> Tuple[Optional[bytes], bytes]:
        # takes the first complete frame off a receive buffer, skipping any
        # bytes before its magic; returns (body or None, remaining buffer)
        start = data.find(cls.FRAME_MAGIC)
        if start < 0 or len(data) - start < 4:
            return None, data
        length = struct.unpack("<H", data[start + 2:start + 4])[0]
        end = start + 4 + length
        if len(data) < end:
            return None, data
        return data[start + 4:end], data[end:]

    @classmethod
    def new_print_id(cls) -> int:
        # same scheme as the vendor app, kept positive for the firmware's
        # signed int; two notes inside one millisecond must still differ
        print_id = int(time.time() * 1000) & 0x7FFFFFFF
        if print_id == cls._last_print_id:
            print_id = (print_id + 1) & 0x7FFFFFFF
        cls._last_print_id = print_id
        return print_id

    @classmethod
    def _encode_bmp(cls, image: Image.Image) -> str:
        # 1-bpp bmp, where a 0 bit is ink - pillow writes the palette this way
        if image.mode != "1":
            image = image.convert("1")
        # bmp stores rows bottom-up but the firmware prints them in stored
        # order, so flip to bring the top of the image out first
        buffer = io.BytesIO()
        ImageOps.flip(image).save(buffer, format="BMP")
        raw = bytearray(buffer.getvalue())

        for offset in cls._BMP_ZEROED_OFFSETS:
            raw[offset:offset + 4] = b"\x00\x00\x00\x00"

        # the vendor app leaves 0xff in the palette reserved bytes; pillow
        # writes 0x00 there
        raw[57] = 0xFF
        raw[61] = 0xFF

        return base64.b64encode(bytes(raw)).decode("ascii")

    @classmethod
    def image_element(cls, image: Image.Image) -> Dict[str, Any]:
        return {
            "basetext": cls._encode_bmp(image),
            "bold": 0,
            "encodeType": 0,
            "fontSize": 1,
            "iconID": 0,
            "isLeaveWhite": False,
            "isSignature": False,
            "printType": cls.TYPE_IMAGE,
            "underline": 0,
        }

    @classmethod
    def build_job(
        cls,
        elements: List[Dict[str, Any]],
        mac_address: str,
        device_name: str,
        user_id: str,
        print_id: Optional[int] = None,
    ) -> bytes:
        # one framed single-package note, fields as the vendor app sends them
        job = {
            "blueAdd": mac_address.replace(":", "").upper(),
            "blueDevName": device_name,
            "command": cls.COMMAND_PRINT,
            "content": {"textList": elements},
            "encryptFlag": 0,
            "hasHead": 1,
            "hasSignature": 0,
            "hasTail": 1,
            "hasTimer": 1,
            "isFromTtemplate": False,
            "msgType": 1,
            "paperType": 0,
            "pkgCount": 1,
            "pkgNo": 1,
            "printID": print_id if print_id is not None else cls.new_print_id(),
            "priority": 0,
            "result": 0,
            "strDate": time.strftime("%Y-%m-%d %H:%M:%S"),
            "toUserId": user_id,
            "userId": user_id,
        }
        # the vendor app emits keys alphabetically with no whitespace
        payload = json.dumps(job, separators=(",", ":"), sort_keys=True)
        return cls.frame(payload.encode("utf-8"))

    @classmethod
    def build_cut_job(cls, mac_address: str, device_name: str, user_id: str) -> bytes:
        # a note holding one blank row: printing it leaves no mark, and
        # finishing it makes the firmware cut
        blank = Image.new("1", (cls.PRINTER_WIDTH, 1), 1)
        return cls.build_job(
            [cls.image_element(blank)], mac_address, device_name, user_id
        )
