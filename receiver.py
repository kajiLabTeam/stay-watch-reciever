import json
import datetime
import time
import subprocess
import multiprocessing
import sqlite3
import requests
import datetime
from urllib3.util import Retry
from requests.adapters import HTTPAdapter
import schedule


class DataLogger():
    def __init__(self, fn):
        self.fn = fn

    # テキストファイルにスキャン結果を書き込む(追記モード)
    def append_line(self, line):
        with open(self.fn, "a") as f:
            f.write(line + '\n')


# データベースとのコネクションを確立する関数
def connect_db():
    conn = sqlite3.connect('/home/pi/stay-watch-reciever/log.db')
    return conn


def update_log(address, date, rssi):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute('UPDATE users set date=?, rssi=? WHERE address=?',
                (date, rssi, address))
    conn.commit()
    conn.close()


def reset_hci():
    # resetting bluetooth dongle
    cmd = "sudo hciconfig hci1 down"
    subprocess.call(cmd, shell=True)
    cmd = "sudo hciconfig hci1 up"
    subprocess.call(cmd, shell=True)
    cmd = "sudo hciconfig hci1 reset"
    a = subprocess.call(cmd, shell=True)
    return a


# スキャン結果のデータに関するクラス
class LeAdvertisingReport():
    def __init__(self):
        self.company = None
        self.type = None
        self.mac_address = None
        self.uuid = None
        self.rssi = None
        self.tx_power = None
        self.timestamp = datetime.datetime.now()    # 現在時刻を取得して格納

    # 文字列からCompany名を抜き出す関数
    def set_company(self, line):
        if line.startswith('Company: '):
            self.company = line.split(': ')[1]

    # 文字列からTypeを抜き出す関数
    def set_type(self, line):
        if line.startswith('Type: '):
            self.type = line.split(': ')[1]

    # 文字列からMAC Addressを抜き出す関数
    def set_mac_address(self, line):
        if line.startswith('Address: '):
            self.mac_address = line.split(' ')[1]

    # 文字列からUUIDを抜き出す関数
    def set_uuid(self, line):
        if line.startswith('UUID: '):
            self.uuid = line.split(': ')[1]

    # 文字列からTX powerを抜き出す関数
    def set_tx_power(self, line):
        if line.startswith('TX power: '):
            self.tx_power = int(line.split(': ')[1].split(' ')[0])

    # 文字列からRSSI値を抜き出す関数
    def set_rssi(self, line):
        if line.startswith('RSSI: '):
            self.rssi = int(line.split(': ')[1].split(' ')[0])

    def event_detected(self):
        global user_id
        # 特定のMacアドレスを含むモノ以外は除外する
        # if 'XX:XX' not in self.mac_address:
        #    return

        # 検知レポートを表示
        # print('<LeAdvertisingReport@{}>'.format(self.timestamp))
        # print('company={}'.format(self.company))
        # print('type={}'.format(self.type))
        # print('mac_address={}'.format(self.mac_address))
        # print('UUID={}'.format(self.uuid))
        # print('tx_power={} dB'.format(self.tx_power))
        # print('rssi={} dBm'.format(self.rssi))

        # データベースに記録する
        if self.mac_address in user_id:
            update_log(self.mac_address, self.timestamp, self.rssi)

        # 距離の算出
        # d = None
        # if self.tx_power and self.rssi:
        #     d = pow(10.0, (self.tx_power - self.rssi) / 20.0)
        #     print('Distance = {} m'.format(d))

        # ログとしてローカルに書き出す
        # tmp = {
        #         'timestamp': self.timestamp.isoformat(),
        #         'company': self.company,
        #         'mac_address': self.mac_address,
        #         'UUID': self.uuid,
        #         'tx_power': self.tx_power,
        #         'rssi': self.rssi,
        #         'distance': d
        # }

        # テキストファイルに取得したデータを書き込む
        # DataLogger('result.txt').append_line(json.dumps(tmp))


def run_lescan():
    while True:
        process = subprocess.Popen('hcitool lescan --duplicates',
                                   shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        while True:
            output = process.stdout.readline()

            # process.poll()で終了を確認する(終了していなかったらNone，終了していたらそのステータスが返る．)
            if process.poll() is not None:
                break

            if output:
                #print('lescan >>>', output.strip())
                pass


def run_btmon():
    # 標準出力に '> HCI Event: LE Meta Event' の文字列が入っているかをTrue, Falseで返す関数内関数
    def _is_new_event(line):
        return '> HCI Event: LE Meta Event' in line

    tmp = None
    while True:
        process = subprocess.Popen(
            'btmon', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        while True:
            output = process.stdout.readline()  # バッファから1行読み込む(出力がリアルタイムで改行されるたびに取得が可能)

            # process.poll()で終了を確認する(終了していなかったらNone，終了していたらそのステータスが返る．)
            if process.poll() is not None:
                break

            # outputの中身がNoneでなければ下記の処理を行う
            if output:
                try:
                    # outputの中身はbytes型なので文字列に変換する．また文字列の両端の連続する空白文字等を取り除く
                    line = output.decode('utf-8').strip()
                except:
                    break

                # HCI Eventを拾い上げる
                if _is_new_event(line):
                    if tmp is not None:
                        tmp.event_detected()
                    tmp = LeAdvertisingReport()
                    continue

                # イベントが検知されるまで待つ
                if tmp is None:
                    continue

                # コマンド出力をパースする
                try:
                    tmp.set_company(line)
                    tmp.set_type(line)
                    tmp.set_mac_address(line)
                    tmp.set_uuid(line)
                    tmp.set_tx_power(line)
                    tmp.set_rssi(line)
                except Exception:
                    print('Failed to parse.')


# データをサーバにPOSTする関数
def post_data():

    read_datas = []

    conn = connect_db()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, rssi FROM users WHERE date IS NOT NULL")
    except:
        conn.close()

    for i in cur.fetchall():
        read_datas.append({'id': i[0], 'rssi': i[1]})

    # サーバに送信するデータ
    post_datas = {"member": read_datas, "room": "学生部屋"}
    print(post_datas)

    # 実際に送信する処理(前のコード)
    # res = requests.post('https://kajilab.net/stay-watch/update',
    #                     data=json.dumps(post_datas),
    #                     headers={'Content-Type': 'application/json'})
    # print(res.status_code)

    # サーバーのURL
    server_url = "https://kajilab.net/stay-watch/update"

    with requests.Session() as session:

        # リトライの設定
        retries = Retry(total=5,  # リトライ回数
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

    # dateをNULLにする
    try:
        cur.execute(
            'UPDATE users set date=?, rssi=? WHERE date IS NOT NULL', (None, None))
        conn.commit()
        conn.close()
    except:
        conn.close()

    # print(datetime.datetime.now())


if __name__ == '__main__':
    global user_id
    post_interval = 3     # 3分

    print("START!!")

    # macアドレスとID対応表(辞書型)を作成
    conn = connect_db()
    cur = conn.cursor()
    address = [i[0] for i in cur.execute("SELECT address FROM users")]
    ids = [i[0] for i in cur.execute("SELECT id FROM users")]
    user_id = {k: v for k, v in zip(address, ids)}
    conn.close()

    p1 = multiprocessing.Process(target=run_lescan, args=())
    p1.daemon = True  # デーモンとして実行する(プログラムを終了させたときsubprocessで動かしているものも終了させる)
    p1.start()

    p2 = multiprocessing.Process(target=run_btmon, args=())
    p2.daemon = True
    p2.start()

    # p3 = multiprocessing.Process(target=post_data, args=(post_interval,))
    # p3.daemon = True
    # p3.start()

    # 2分間待機
    time.sleep(120)
    post_data()
    p1.terminate()
    p2.terminate()

    # schedule.every(post_interval).minutes.do(post_data)

    # while True:
    #     schedule.run_pending()
    #     time.sleep(1)
