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
import sqlite3

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


def judge_unique(value):
    global sent_datas
    uuid_list = [i['uuid'] for i in sent_datas]
    if value in uuid_list:
        return False
    else:
        return True


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

                if(val[8:12] == 'e7d6' and val[8:40] != 'e7d61ea3f8dd49c88f2ff2484c07acb9' and judge_unique(val[8:40])):
                    sent_datas.append(
                        {'uuid': val[8:40], 'rssi': int(dev.rssi)})
                    # print("UUID: " + val[8:40])

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

# データをDBに書き込む関数
def write_db():
    global sent_datas
    for d in sent_datas:
        insert_log(d['uuid'], d['rssi'])
        print('{}: {}'.format(d['uuid'], d['rssi']))


# データベースとのコネクションを確立する関数
def connect_db():
    conn = sqlite3.connect('./tmpLog.db')
    return conn


def insert_log(uuid, rssi):
    conn = connect_db()
    cur = conn.cursor()
    # cur.execute('select uuid from users')
    cur.execute('select * from users where uuid = ?',[uuid])

    # uuidが存在しない場合のみ追加
    cur.execute("SELECT * FROM users WHERE uuid = ?", (uuid,))
    if cur.fetchone() is None:
        cur.execute("INSERT INTO users (uuid, rssi,count) VALUES(?, ? , 1)", (uuid, rssi))
    else:
        for row in cur:            
            print(row)        
        cur.execute("UPDATE users SET rssi=?,count=? where uuid=?",(row[1]+rssi,row[2]+1,uuid))

    conn.commit()
    conn.close()

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

    write_db()


if __name__ == "__main__":
    main()
