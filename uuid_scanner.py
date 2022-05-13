from __future__ import print_function
import argparse
import binascii
import os
import sys
from bluepy import btle
import json
import requests
from urllib3.util import Retry
from requests.adapters import HTTPAdapter

if os.getenv('C', '1') == '0':
    ANSI_RED = ''
    ANSI_GREEN = ''
    ANSI_YELLOW = ''
    ANSI_CYAN = ''
    ANSI_WHITE = ''
    ANSI_OFF = ''
else:
    ANSI_CSI = "\033["
    ANSI_RED = ANSI_CSI + '31m'
    ANSI_GREEN = ANSI_CSI + '32m'
    ANSI_YELLOW = ANSI_CSI + '33m'
    ANSI_CYAN = ANSI_CSI + '36m'
    ANSI_WHITE = ANSI_CSI + '37m'
    ANSI_OFF = ANSI_CSI + '0m'


def dump_services(dev):
    services = sorted(dev.services, key=lambda s: s.hndStart)
    for s in services:
        print("\t%04x: %s" % (s.hndStart, s))
        if s.hndStart == s.hndEnd:
            continue
        chars = s.getCharacteristics()
        for i, c in enumerate(chars):
            props = c.propertiesToString()
            h = c.getHandle()
            if 'READ' in props:
                val = c.read()
                if c.uuid == btle.AssignedNumbers.device_name:
                    string = ANSI_CYAN + '\'' + \
                        val.decode('utf-8') + '\'' + ANSI_OFF
                elif c.uuid == btle.AssignedNumbers.device_information:
                    string = repr(val)
                else:
                    string = '<s' + binascii.b2a_hex(val).decode('utf-8') + '>'
            else:
                string = ''
            print("\t%04x:    %-59s %-12s %s" % (h, c, props, string))

            while True:
                h += 1
                if h > s.hndEnd or (i < len(chars) - 1 and h >= chars[i + 1].getHandle() - 1):
                    break
                try:
                    val = dev.readCharacteristic(h)
                    print("\t%04x:     <%s>" %
                          (h, binascii.b2a_hex(val).decode('utf-8')))
                except btle.BTLEException:
                    break


class ScanPrint(btle.DefaultDelegate):

    def __init__(self, opts):
        btle.DefaultDelegate.__init__(self)
        self.opts = opts

    def handleDiscovery(self, dev, isNewDev, isNewData):
        if isNewDev:
            status = "new"
        elif isNewData:
            if self.opts.new:
                return
            status = "update"
        else:
            if not self.opts.all:
                return
            status = "old"

        if dev.rssi < self.opts.sensitivity:
            return

        # BLEビーコンのUUIDを取得
        global sent_datas
        for (sdid, desc, val) in dev.getScanData():
            if len(val) == 50:
                # sent_datas.append([val[8:40], int(dev.rssi)])

                if(val[8:12] == 'e7d6'):
                    sent_datas.append(
                        {'uuid': val[8:40], 'rssi': int(dev.rssi)})
                    print("UUID: " + val[8:40])

        # print ('    Device (%s): %s (%s), %d dBm %s' %
        #        (status,
        #            ANSI_WHITE + dev.addr + ANSI_OFF,
        #            dev.addrType,
        #            dev.rssi,
        #            ('' if dev.connectable else '(not connectable)'))
        #        )
        # for (sdid, desc, val) in dev.getScanData():
        #     if sdid in [8, 9]:
        #         print ('\t' + desc + ': \'' + ANSI_CYAN + val + ANSI_OFF + '\'')

        #     else:
        #         print ('\t' + desc + ': <' + val + '>')

        # if not dev.scanData:
        #     print ('\t(no data)')
        # print

# データをサーバにPOSTする関数


def post_data():
    global sent_datas

    # サーバに送信するデータ
    post_datas = {"Beacons": sent_datas, "roomID": 1}
    print(post_datas)

    # サーバーのURL
    server_url = "https://go-staywatch.kajilab.tk/room/v1/beacon"

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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--hci', action='store', type=int, default=0,
                        help='Interface number for scan')
    parser.add_argument('-t', '--timeout', action='store', type=int, default=4,
                        help='Scan delay, 0 for continuous')
    parser.add_argument('-s', '--sensitivity', action='store', type=int, default=-128,
                        help='dBm value for filtering far devices')
    parser.add_argument('-d', '--discover', action='store_true',
                        help='Connect and discover service to scanned devices')
    parser.add_argument('-a', '--all', action='store_true',
                        help='Display duplicate adv responses, by default show new + updated')
    parser.add_argument('-n', '--new', action='store_true',
                        help='Display only new adv responses, by default show new + updated')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Increase output verbosity')
    arg = parser.parse_args(sys.argv[1:])

    btle.Debugging = arg.verbose

    global sent_datas
    sent_datas = []

    scanner = btle.Scanner(arg.hci).withDelegate(ScanPrint(arg))

    print(ANSI_RED + "Scanning for devices..." + ANSI_OFF)

    try:
        devices = scanner.scan(arg.timeout)
    except:
        pass

    if arg.discover:
        print(ANSI_RED + "Discovering services..." + ANSI_OFF)

        for d in devices:
            if not d.connectable or d.rssi < arg.sensitivity:

                continue

            print("    Connecting to", ANSI_WHITE + d.addr + ANSI_OFF + ":")

            dev = btle.Peripheral(d)
            dump_services(dev)
            dev.disconnect()

    post_data()


if __name__ == "__main__":
    main()
