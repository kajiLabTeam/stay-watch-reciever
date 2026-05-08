from __future__ import annotations

from dataclasses import dataclass

KAJILAB_TEST_UUID_BLACKLIST = {"e7d61ea3f8dd49c88f2ff2484c07acb9"}

PHYSICAL_BEACON_LEN = 50
IPHONE_BG_BEACON_LEN = 38
ANDROID_BEACON_LEN = 36

PRIV_BEACON_PREFIX = "ffff"
PHYSICAL_PREFIX_KAJILAB = "8ebc"
PHYSICAL_PREFIX_E7D6 = "e7d6"
IPHONE_PREFIX = "4c0001"
ANDROID_HEAD = "8ebc2114"
ANDROID_MID = "4abd"
PRIVACY_HEAD_MIN_EXCLUSIVE = 63
PRIVACY_HEAD_MAX_EXCLUSIVE = 128


@dataclass(frozen=True)
class Beacon:
    uuid: str
    msd: str
    rssi: int


def _compose_36(val: str) -> str:
    return val[0:8] + val[9:13] + val[14:18] + val[19:23] + val[24:36]


def parse_ad_value(val: str, rssi: int, seen_uuids: set[str]) -> list[Beacon]:
    """Parse a single advertisement payload into 0+ Beacon entries.

    `seen_uuids` is mutated to deduplicate UUIDs across a scan session.
    """
    beacons: list[Beacon] = []

    if val[:4] == PRIV_BEACON_PREFIX:
        beacons.append(Beacon(uuid="", msd=val, rssi=rssi))

    if len(val) == PHYSICAL_BEACON_LEN:
        prefix = val[8:12]
        body = val[8:40]
        if prefix == PHYSICAL_PREFIX_KAJILAB and body not in seen_uuids:
            seen_uuids.add(body)
            beacons.append(Beacon(uuid=body, msd="", rssi=rssi))
        elif (
            prefix == PHYSICAL_PREFIX_E7D6
            and body not in KAJILAB_TEST_UUID_BLACKLIST
            and body not in seen_uuids
        ):
            seen_uuids.add(body)
            beacons.append(Beacon(uuid=body, msd="", rssi=rssi))
    elif len(val) == IPHONE_BG_BEACON_LEN:
        if val[0:6] == IPHONE_PREFIX and val not in seen_uuids:
            seen_uuids.add(val)
            beacons.append(Beacon(uuid=val, msd="", rssi=rssi))
    elif len(val) == ANDROID_BEACON_LEN:
        composed = _compose_36(val)
        if val[0:8] == ANDROID_HEAD and val[9:13] == ANDROID_MID:
            if composed not in seen_uuids:
                seen_uuids.add(composed)
                beacons.append(Beacon(uuid=composed, msd="", rssi=rssi))
        else:
            try:
                head = int(val[:2], 16)
            except ValueError:
                head = -1
            if (
                PRIVACY_HEAD_MIN_EXCLUSIVE < head < PRIVACY_HEAD_MAX_EXCLUSIVE
                and composed not in seen_uuids
            ):
                seen_uuids.add(composed)
                beacons.append(Beacon(uuid=composed, msd="", rssi=rssi))

    return beacons
