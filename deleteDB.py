import requests
from urllib3.util import Retry
from requests.adapters import HTTPAdapter
import json
import sqlite3

# データベースとのコネクションを確立する関数


def connect_db():
    conn = sqlite3.connect('./tmpLog.db')
    return conn


def delete_db():
    print('delete')
    conn = connect_db()
    cur = conn.cursor()
    cur.execute('DELETE FROM users')
    conn.commit()


if __name__ == "__main__":
    delete_db()
