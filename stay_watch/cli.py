from __future__ import annotations

import argparse

from stay_watch import db
from stay_watch.config import (
    DEFAULT_HCI_INDEX,
    DEFAULT_RSSI_THRESHOLD,
    DEFAULT_SCAN_TIMEOUT,
)


def _cmd_init(_: argparse.Namespace) -> None:
    db.init_db()
    print("initialized DB")


def _cmd_scan(args: argparse.Namespace) -> None:
    from stay_watch import scanner

    n = scanner.scan_to_db(
        timeout=args.timeout, hci=args.hci, sensitivity=args.sensitivity
    )
    print(f"scanned and wrote {n} beacons")


def _cmd_post(_: argparse.Namespace) -> None:
    from stay_watch import poster

    poster.post_and_clear()


def _cmd_clear(_: argparse.Namespace) -> None:
    db.clear()
    print("cleared users table")


def main() -> None:
    parser = argparse.ArgumentParser(prog="stay_watch")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="initialize SQLite DB")
    p_init.set_defaults(func=_cmd_init)

    p_scan = sub.add_parser("scan", help="run a single BLE scan and write to DB")
    p_scan.add_argument("-t", "--timeout", type=int, default=DEFAULT_SCAN_TIMEOUT)
    p_scan.add_argument("-i", "--hci", type=int, default=DEFAULT_HCI_INDEX)
    p_scan.add_argument(
        "-s", "--sensitivity", type=int, default=DEFAULT_RSSI_THRESHOLD
    )
    p_scan.set_defaults(func=_cmd_scan)

    p_post = sub.add_parser("post", help="aggregate DB rows and POST to server")
    p_post.set_defaults(func=_cmd_post)

    p_clear = sub.add_parser("clear", help="delete all rows from users table")
    p_clear.set_defaults(func=_cmd_clear)

    args = parser.parse_args()
    args.func(args)
