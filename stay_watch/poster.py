from __future__ import annotations

import json

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

from stay_watch import config, db


def _build_session() -> requests.Session:
    session = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=2,
        status_forcelist=[500, 502, 503, 504],
    )
    session.mount(config.SERVER_URL, HTTPAdapter(max_retries=retries))
    return session


def post_and_clear() -> int:
    beacons = db.aggregated_beacons()
    db.clear()

    payload = {"beacons": beacons, "roomId": config.ROOM_ID}
    print(payload)

    with _build_session() as session:
        response = session.post(
            url=config.SERVER_URL,
            headers={
                "Content-Type": "application/json",
                "X-API-Key": config.STAYWATCH_API_KEY,
            },
            data=json.dumps(payload),
            timeout=(10.0, 30.0),
        )

    print(f"Response = {response.status_code}")
    return response.status_code
