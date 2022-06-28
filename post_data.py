import requests
from urllib3.util import Retry
from requests.adapters import HTTPAdapter
import json
import sqlite3
import math
import os
from dotenv import load_dotenv
# .envファイルの内容を読み込見込む
load_dotenv()


# データをサーバにPOSTする関数
def post_data(sent_datas):

    # サーバに送信するデータ
    post_datas = {"Beacons": sent_datas, "roomID": os.environ['ROOM_ID']}
    print(post_datas)

    # サーバーのURL
    server_url = "https://go-staywatch.kajilab.tk/room/v1/beacon"

    with requests.Session() as session:

        # リトライの設定
        retries = Retry(
            total=5,  # リトライ回数
            backoff_factor=2,  # sleep時間
            status_forcelist=[500, 502, 503, 504])  # timeout以外でリトライするステータスコード

        # セッションを確立
        session.mount(server_url, HTTPAdapter(max_retries=retries))

        # connect timeoutを10秒, read timeoutを30秒に設定
        response = session.post(url=server_url,
                                headers={'Content-Type': 'application/json'},
                                data=json.dumps(post_datas),
                                stream=True,
                                timeout=(10.0, 30.0))

        print('Response = {}\n'.format(response.status_code))


# データベースとのコネクションを確立する関数
def connect_db():
    conn = sqlite3.connect('/home/pi/stay-watch-reciever/tmpLog.db')
    return conn


def read_db():
    conn = connect_db()
    cur = conn.cursor()
    read_datas = cur.execute('SELECT uuid, rssi, count FROM users')
    return read_datas


def delete_db():
    conn = connect_db()
    cur = conn.cursor()
    cur.execute('DELETE FROM users')
    conn.commit()


def main():
    # DBから在室者のデータを取得
    read_datas = [{'uuid': d[0], 'rssi': math.floor(
        d[1]/d[2])} for d in read_db()]

    # 形式を整えてサーバに送信
    post_data(read_datas)

    # DBを初期化する
    delete_db()


if __name__ == '__main__':
    main()
