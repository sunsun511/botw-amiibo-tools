"""Create an emulator-only plain NTAG215 fixture; never a physical NFC dump.

Layout: Service::NFP::NTAG215File from the Yuzu/Eden source lineage.
No retail keys, copied tag dumps, owner Mii, or game save data are used.
This is NOT confirmed on Suyu dev-0de49070e4; test in-game before relying on it.
"""
from pathlib import Path
import hashlib
import json
import struct
from datetime import date

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / 'link_archer_plain_test.bin'
MODEL_ID = bytes.fromhex('0100000003530902')


def build():
    b = bytearray(0x21C)
    # Stable synthetic identifier: repeating the script does not change identity.
    uid = bytes.fromhex('0492a163274b80')
    b[0] = uid[3] ^ uid[4] ^ uid[5] ^ uid[6]
    b[1] = 0x48
    struct.pack_into('<HI', b, 2, 0xE00F, 0xEEFF10F1)
    b[0x28] = 0xA5
    # Deliberately unregistered: no fabricated owner-Mii or application save.
    b[0x2C] = 0
    d = date(2026, 9, 20)
    encoded_date = ((d.year - 2000) << 9) | (d.month << 5) | d.day
    struct.pack_into('>HH', b, 0x30, encoded_date, encoded_date)
    b[0x38:0x4C] = 'LinkTest'.encode('utf-16-be').ljust(20, b'\0')
    b[0x1D4:0x1D7] = uid[:3]
    b[0x1D7] = 0x88 ^ uid[0] ^ uid[1] ^ uid[2]
    b[0x1D8:0x1DC] = uid[3:]
    b[0x1DC:0x1E4] = MODEL_ID
    struct.pack_into('<III', b, 0x208, 0x0F0001, 0x04000000, 0x5F)
    return bytes(b)


def validate_plain(payload):
    """Translate key fields into physical layout, then check upstream constants.

    This verifies file structure only, not actual emulation or BOTW drops.
    """
    if len(payload) != 540:
        return False
    nfc = bytearray(540)
    nfc[0:8] = payload[0x1D4:0x1DC]
    nfc[8:16] = payload[0:8]
    nfc[0x54:0x60] = payload[0x1DC:0x1E8]
    nfc[0x208:] = payload[0x208:]
    return all((
        nfc[3] == (0x88 ^ nfc[0] ^ nfc[1] ^ nfc[2]),
        nfc[8] == (nfc[4] ^ nfc[5] ^ nfc[6] ^ nfc[7]),
        int.from_bytes(nfc[10:12], 'little') == 0xE00F,
        int.from_bytes(nfc[12:16], 'little') == 0xEEFF10F1,
        nfc[0x5B] == 2,
        (int.from_bytes(nfc[0x208:0x20C], 'little') & 0xFFFFFF) == 0x0F0001,
        int.from_bytes(nfc[0x20C:0x210], 'little') == 0x04000000,
        int.from_bytes(nfc[0x210:0x214], 'little') == 0x5F,
    ))


def main():
    b = build()
    assert validate_plain(b)
    assert b[0x1DC:0x1E4] == MODEL_ID
    # Reject truncation and corrupt UID/constants instead of accepting arbitrary .bin.
    assert not validate_plain(b[:-1])
    for offset in (0, 2, 4, 0x1D7, 0x1E3, 0x208, 0x20F, 0x210):
        bad = bytearray(b)
        bad[offset] ^= 1
        assert not validate_plain(bad), hex(offset)
    if OUTPUT.exists():
        if OUTPUT.read_bytes() != b:
            raise FileExistsError(f'Refusing to replace modified file: {OUTPUT}')
    else:
        with OUTPUT.open('xb') as f:
            f.write(b)
    report = {
        'file': OUTPUT.name,
        'bytes': len(b),
        'sha256': hashlib.sha256(b).hexdigest(),
        'identity': 'Link - Archer',
        'model_id': MODEL_ID.hex(),
        'format': 'plain NTAG215File (emulator internal layout), NOT physical NFC layout',
        'structure_checks': 'PASS; length + 8 corruption cases rejected',
        'registration': 'not initialized; no owner Mii or application area',
        'suyu_target': 'dev-0de49070e4 (2024-04-10)',
        'suyu_exact_source_verified': False,
        'in_game_test': 'NOT RUN: user Steam Deck required',
        'retail_keys_used': False,
        'sources': [
            'https://raw.githubusercontent.com/eden-emulator/mirror/master/src/core/hle/service/nfp/nfp_types.h',
            'https://raw.githubusercontent.com/eden-emulator/mirror/master/src/core/hle/service/nfc/common/amiibo_crypto.cpp',
            'https://raw.githubusercontent.com/eden-emulator/mirror/master/src/core/hle/service/nfc/common/device.cpp',
            'https://raw.githubusercontent.com/N3evin/AmiiboAPI/master/database/amiibo.json',
            'https://yuzu-mirror.github.io/entry/yuzu-progress-report-mar-2023/',
        ],
    }
    report_path = ROOT / 'validation.json'
    content = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    if not report_path.exists():
        with report_path.open('x', encoding='utf-8') as f:
            f.write(content)
    print(content)


if __name__ == '__main__':
    main()
