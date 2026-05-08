from __future__ import annotations

import sys

from bluepy import btle

from stay_watch import beacon, db
from stay_watch.config import DEFAULT_HCI_INDEX, DEFAULT_RSSI_THRESHOLD


class _ScanCollector(btle.DefaultDelegate):
    def __init__(self, sensitivity: int) -> None:
        super().__init__()
        self._sensitivity = sensitivity
        self.beacons: list[beacon.Beacon] = []
        self._seen_uuids: set[str] = set()

    def handleDiscovery(self, dev, isNewDev, isNewData) -> None:  # noqa: N802 (bluepy API)
        if dev.rssi < self._sensitivity:
            return
        rssi = int(dev.rssi)
        for (_sdid, _desc, val) in dev.getScanData():
            self.beacons.extend(
                beacon.parse_ad_value(val, rssi, self._seen_uuids)
            )


def scan(
    timeout: int,
    hci: int = DEFAULT_HCI_INDEX,
    sensitivity: int = DEFAULT_RSSI_THRESHOLD,
) -> list[beacon.Beacon]:
    collector = _ScanCollector(sensitivity)
    scanner_obj = btle.Scanner(hci).withDelegate(collector)
    try:
        scanner_obj.scan(timeout)
    except btle.BTLEException as e:
        print(f"BTLE scan error: {e}", file=sys.stderr)
    return collector.beacons


def scan_to_db(
    timeout: int,
    hci: int = DEFAULT_HCI_INDEX,
    sensitivity: int = DEFAULT_RSSI_THRESHOLD,
) -> int:
    db.init_db()
    beacons = scan(timeout, hci, sensitivity)
    if not beacons:
        return 0
    with db.connect() as conn:
        for b in beacons:
            db.upsert_beacon(conn, b.uuid, b.msd, b.rssi)
    return len(beacons)
