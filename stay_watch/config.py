from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(os.getenv("STAY_WATCH_ROOT", "/home/pi/stay-watch-reciever"))
DB_PATH = Path(os.getenv("STAY_WATCH_DB_PATH", str(PROJECT_ROOT / "tmpLog.db")))

ROOM_ID = int(os.getenv("ROOM_ID", "0"))
STAYWATCH_API_KEY = os.getenv("STAYWATCH_API_KEY", "")
SERVER_URL = os.getenv(
    "STAYWATCH_SERVER_URL",
    "https://staywatch-backend.kajilab.net/api/v1/stayers",
)

DEFAULT_SCAN_TIMEOUT = 60
DEFAULT_RSSI_THRESHOLD = -128
DEFAULT_HCI_INDEX = 0
