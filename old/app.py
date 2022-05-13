#!/home/kajilab/.pyenv/versions/3.6.12/bin/python
# -*- coding: utf-8 -*-


from flask import Flask, render_template, request, jsonify, make_response, abort
import mysql.connector as mydb
from datetime import datetime, date, timedelta
from flask_cors import CORS


app = Flask(__name__)
CORS(app)
app.config['JSON_AS_ASCII'] = False  # 日本語文字化け対策
app.config["JSON_SORT_KEYS"] = False  # ソートをそのまま


# データベースとのコネクションを確立する関数
def connect_db():
    conn = mydb.connect(
        host='mysql57.kajilab.sakura.ne.jp',
        port='3306',
        user='kajilab',
        password='kaj1labkaj1lab',
        database='kajilab_staywatch'
    )

    # コネクションが切れた時に再接続してくれるよう設定
    conn.ping(reconnect=True)

    # 接続できているかどうか確認
    # print(conn.is_connected())
    return conn


# 滞在履歴のデータから合計滞在時間(秒)を計算する関数
def calc_total_time(data):
    """
    :param data: str型: periodのデータ 例:11:34:01~11:55:02,12:07:02~13:43:05,13:46:04~13:58:05,
    :return:
    """
    # カンマ区切りで文字列を分ける
    split_txt = data.split(',')

    # dataが空だった時は0を返す
    if len(split_txt) == 0:
        return 0

    total_time = 0

    # split_txtの中身は「,」で区切った文字列をリストに格納した物なので、さらにそれをループで回す
    for i in split_txt:

        # iの中身が空ならループを抜ける
        if len(i) == 0:
            break

        # 「~」で文字列を区切る
        # 例. 10:56:14~10:56:15 を「10:56:14」と「10:56:15」に分ける
        try:
            tmp = i.split('~')
        except:
            break

        # 実際に時間を計算する(秒)
        try:
            if len(tmp[1]) != 0:
                # 時間の文字列をdatetime型に変換する
                start = datetime.strptime(tmp[0], '%H:%M:%S')
                finish = datetime.strptime(tmp[1], '%H:%M:%S')
                td = finish - start
                total_time += td.seconds
        except:
            break

    return total_time


# 返却するJSONデータのフォーマットを整える関数
def make_return_dict(keys, datas):
    return_json = []

    for data in datas:
        return_json.append(dict(zip(keys, data)))

    return return_json

# periodのデータ(カンマ区切りの時間の文字列)を辞書型のリストに変換する関数


def make_period_dict(text):
    """
    :param text: str型:periodのデータ 例:11:34:01~11:55:02,12:07:02~13:43:05,13:46:04~13:58:05,
    :return: list型: periodを辞書型にしてlistに入れたもの
    """
    return_list = []

    for i in text.split(','):
        if len(i) > 0:
            return_list.append({
                'enterTime': i.split('~')[0],
                'exitTime': i.split('~')[1]
            })

    return return_list

# IDを情報を基に名前を取得する関数
def ID_to_name(cur, text):
    return_list = []

    # IDを名前に変換する
    for i in text.split(','):
        if len(i) > 0:
            cur.execute("SELECT name FROM ID WHERE ID.ID=%s", (i, ))
            return_list.append(cur.fetchall()[0][0])
    # 名前を降順でソートして返却
    return sorted(return_list)


# periodのデータ(カンマ区切りの時間の文字列)に改行タグ(<br>)を入れる関数
def make_web_format(text):

    return_str = ''

    for i in text.split(','):
        if len(i) > 0:
            return_str += i + ',<br>'

    return return_str


# 受け取ったデータを基にnowテーブルを更新する関数
def update_now_table(cur, conn, receive_room, receive_members):
    # もし、受け取ったデータが空なら何もしない
    if len(receive_members) == 0:
        return receive_members

    cur.execute("SELECT ID FROM ID WHERE operable=1")  # データベースに登録されているID一覧を取得
    regist_id = [i[0] for i in cur.fetchall()]  # 1次元のlistに変換
    del_num = []

    # 受け取ったデータの中からデータベースに登録されていないIDを探す

    for i in range(len(receive_members)):
        if receive_members[i]['id'] not in regist_id:
            del_num.append(i)

    # 実際に削除する(そのまま削除するとインデックスがずれてしまうので、インデックスが大き方から削除する)
    for i in sorted(del_num, reverse=True):
        del receive_members[i]

    # 受け取ったデータをnowテーブルに反映(UPDATE)
    for member in receive_members:
        cur.execute("UPDATE now SET room=%s, rssi=%s, flag=%s WHERE ID=%s",
                    (receive_room, member['rssi'], 1, member['id']))
        conn.commit()   # 変更をコミットする

    return receive_members


def update_groupEntryLog_table(cur, conn, date, time, receive_data):

    # 受け取ったデータからidだけを抜き出してカンマ区切りの文字列とリストを作成
    receive_ids = ''
    receive_ids_list = []
    for member in receive_data:
        receive_ids += member['id'] + ','
        receive_ids_list.append(member['id'])

    # 今日の日付のログデータを検索する
    cur.execute("SELECT ids FROM groupEntryLog WHERE date=%s", (date, ))
    today_data = cur.fetchall()

    # もし、ログデータ数が0、かつ受け取ったデータ個数が2個以上ならそのまま追記する(finalFlagを1にして)
    if len(today_data) == 0 and len(receive_data) >= 2:
        cur.execute("INSERT INTO groupEntryLog (date, entryTime, ids, finalFlag) VALUES (%s, %s, %s, %s)",
                    (date, date + ' ' + time, receive_ids, 1))
        conn.commit()   # 変更をコミットする

    # もし、ログデータ数が1以上、かつ受け取ったデータの個数が2個以上ならfinalFlagが1のデータを検索してidsの中身を比較する
    elif len(today_data) >= 1 and len(receive_data) >= 2:

        # groupEntryLogテーブルからflagが1のexitTimeのデータを取得する
        cur.execute(
            "SELECT exitTime FROM groupEntryLog WHERE date=%s AND finalFlag=1", (date, ))
        exitTime = cur.fetchall()[0][0]

        # もし、exitTimeが空でなければfinalFlagを0にして新しい行にデータを追加する
        if exitTime != None:
            # finalFlagを0にする
            cur.execute(
                'UPDATE groupEntryLog SET finalFlag=%s WHERE date=%s AND finalFlag=1', (0, date))
            conn.commit()   # 変更をコミットする
            # 新しい行に現在のデータを書き込む
            cur.execute("INSERT INTO groupEntryLog (date, entryTime, ids, finalFlag) VALUES (%s, %s, %s, %s)",
                        (date, date + ' ' + time, receive_ids, 1))
            conn.commit()   # 変更をコミットする
            return 0

        # groupEntryLogテーブルから今日の日付でflagが1のidのデータを取得する
        cur.execute(
            "SELECT ids FROM groupEntryLog WHERE date=%s AND finalFlag=1", (date, ))
        saved_ids = cur.fetchall()[0][0]
        saved_ids = saved_ids.strip(',')    # 文字列の一番最後のカンマを削除

        # もし、saved_idsとreceive_ids_listに違いがあればexitTimeに時間を登録して、新しい行に現在のデータを書き込む
        if set(receive_ids_list) != set(saved_ids.split(',')):
            # exitTimeに現在の時間を登録する
            cur.execute('UPDATE groupEntryLog SET exitTime=%s, finalFlag=%s WHERE date=%s AND finalFlag=1',
                        (date + ' ' + time, 0, date))
            conn.commit()   # 変更をコミットする
            # 新しい行に現在のデータを書き込む
            cur.execute("INSERT INTO groupEntryLog (date, entryTime, ids, finalFlag) VALUES (%s, %s, %s, %s)",
                        (date, date + ' ' + time, receive_ids, 1))
            conn.commit()   # 変更をコミットする

    # もし、ログデータ数が1以上で、受け取ったデータが1個以下ならexitTimeに時間が入っているか確認する
    elif len(today_data) >= 1 and len(receive_data) <= 1:
        cur.execute(
            "SELECT exitTime FROM groupEntryLog WHERE date=%s AND finalFlag=1", (date, ))
        save_exitTime = cur.fetchall()
        # もし、exitTimeに時間が入っていなければ現在の時間を入れる
        if save_exitTime[0][0] == None:
            # exitTimeに現在の時間を登録する
            cur.execute('UPDATE groupEntryLog SET exitTime=%s, finalFlag=%s WHERE date=%s AND finalFlag=1',
                        (date + ' ' + time, 1, date))
            conn.commit()   # 変更をコミットする


# ラズパイが送ってきた在室者のビーコン情報をデーやベースに登録する関数
@app.route('/update', methods=['GET', 'POST'])
def get_post():
    if request.method == 'POST':

        # 今日の日付を取得 (例:2019-02-04)
        today = str(date.today())
        time = str(datetime.now().strftime("%H:%M:%S"))

        # GETのパラメータを取得
        # 滞在メンバー情報(ID, rssi), (中身の構造はリスト型→辞書型)
        receive_members = request.json['member']
        receive_room = request.json['room']    # 部屋名

        # データベースに接続
        conn = connect_db()
        cur = conn.cursor()

        # nowテーブル内のflagが0のIDを取得
        # ↓↓↓↓↓↓↓↓↓部屋名を指定する↓↓↓↓↓↓↓↓↓↓cur.execute('SELECT ID FROM now WHERE room="学生部屋" AND flag=0')
        cur.execute('SELECT ID FROM now WHERE flag=0')
        nostay_ids = [i[0] for i in cur.fetchall()]

        # ログテーブル内の今日の日付のログを取得(IDのみ)
        cur.execute("SELECT ID FROM log WHERE date BETWEEN %s AND %s",
                    (today + ' 00:00:00', today + ' 23:59:59'))
        log_ids = cur.fetchall()
        log_ids = [i[0] for i in log_ids]  # log_idsはタプル型が入ったリストなので、一次元のリストに変換

        # 受け取ったデータにデータベースに登録されていないIDが入っていたら消してnowテーブルを更新する
        receive_members = update_now_table(
            cur, conn, receive_room, receive_members)

        # groupEntryLogテーブルを更新する
        try:
            update_groupEntryLog_table(cur, conn, today, time, receive_members)
        except:
            pass

        # 今日のログが1個以上あるなら、送られてきたデータと比較する
        if len(log_ids) > 0:

            # 送られてきたデータが空じゃない時
            if len(receive_members) > 0:
                for member in receive_members:
                    # もしログテーブルにデータが無かったら追加する
                    if not member['id'] in log_ids:
                        cur.execute("INSERT INTO log (date, ID, period, room, rssi) VALUES (%s, %s, %s, %s, %s)", (
                            today, member['id'], time + "~", receive_room, member['rssi']))
                        conn.commit()

                    # 一度部屋を出たが戻ってきた時の処理
                    elif member['id'] in log_ids and member['id'] in nostay_ids:
                        # logテーブルの処理
                        # 該当IDのperiodカラムのデータを取得
                        # cur.execute("SELECT period FROM log WHERE date BETWEEN %s AND %s AND ID=%s", (today + ' 00:00:00', today + ' 23:59:59', member['id']))
                        cur.execute("SELECT period, room FROM log WHERE date BETWEEN %s AND %s AND ID=%s", (
                            today + ' 00:00:00', today + ' 23:59:59', member['id']))
                        tmp = cur.fetchall()[0]
                        log_period = tmp[0]
                        # 該当IDのroomカラムのデータを取得(変更)
                        log_room = tmp[1] + ','

                        # 該当するIDのperiodカラムに退出時間を追記する
                        # cur.execute('UPDATE log SET period=%s WHERE ID=%s AND date=%s', (log_period + time + "~", member['id'], today))
                        # (変更)
                        cur.execute('UPDATE log SET period=%s, room=%s WHERE ID=%s AND date=%s', (
                            log_period + time + "~", log_room + receive_room, member['id'], today))
                        conn.commit()

                # receive_membersは辞書型が入ったリストなので、一次元のリストに変換
                receive_ids = [member['id'] for member in receive_members]

                # ログテーブルにはIDがあるけど、送られてきたデータには同じIDがない時(退出処理)
                for log_id in log_ids:
                    # ログIDが受け取ったIDに入っておらず、かつnostay_idsにも入っていない場合(log_idがどっちにも入っていない時)
                    if log_id not in receive_ids and log_id not in nostay_ids:
                        # nowテーブルの処理(nowテーブルのroom情報と同じなら退出処理する)
                        # 該当IDのroomカラムを空にし、rssiを0にし、flagを0にする
                        cur.execute(
                            'UPDATE now SET room=%s, rssi=%s, flag=%s WHERE ID=%s', ('', 0, 0, log_id))
                        conn.commit()

                        # logテーブルの処理
                        # 該当IDのperiodカラムのデータを取得
                        cur.execute("SELECT period FROM log WHERE date BETWEEN %s AND %s AND ID=%s", (
                            today + ' 00:00:00', today + ' 23:59:59', log_id))
                        log_period = cur.fetchall()[0][0]

                        # 該当するIDのperiodカラムに退出時間を追記する
                        cur.execute('UPDATE log SET period=%s WHERE ID=%s AND date=%s',
                                    (log_period + time + ',', log_id, today))
                        conn.commit()
                        # if log_period[-1] == '~':
                        #     # ログの形式が正しければ追記
                        #     cur.execute('UPDATE log SET period=%s WHERE ID=%s AND date=%s', (log_period + time + ',', log_id, today))
                        #     conn.commit()
                        # else:
                        #     # ログの形式が正しくなければその日のログを初期化する
                        #     cur.execute('DELETE FROM log WHERE ID=%s AND date=%s', (log_id, today))
                        #     conn.commit()

            # 送られてきたデータが空の時(退出処理)
            else:
                # nowテーブル内のflagが1のIDを取得
                # ↓↓↓↓↓↓↓↓↓部屋名を指定する↓↓↓↓↓↓↓↓↓↓(SELECT ID FROM now WHERE room="学生部屋" AND flag=1)
                cur.execute('SELECT ID FROM now WHERE flag=1')
                stay_ids = [i[0] for i in cur.fetchall()]
                for stay_id in stay_ids:
                    # nowテーブルの処理(nowテーブルのroom情報と同じなら退出処理する)
                    # 該当IDのroomカラムを空にし、rssiを0にし、flagを0にする
                    cur.execute(
                        'UPDATE now SET room=%s, rssi=%s, flag=%s WHERE ID=%s', ('', 0, 0, stay_id))
                    conn.commit()
                    # logテーブルの処理
                    # 該当IDのperiodカラムのデータを取得
                    cur.execute("SELECT period FROM log WHERE date BETWEEN %s AND %s AND ID=%s", (
                        today + ' 00:00:00', today + ' 23:59:59', stay_id))
                    log_period = cur.fetchall()[0][0]
                    # 該当するIDのperiodカラムに退出時間を追記する
                    cur.execute('UPDATE log SET period=%s WHERE ID=%s AND date=%s',
                                (log_period + time + ',', stay_id, today))
                    conn.commit()
                    # if log_period[-1] == '~':
                    #     cur.execute('UPDATE log SET period=%s WHERE ID=%s AND date=%s', (log_period + time + ',', stay_id, today))
                    #     conn.commit()
                    # else:
                    #     # ログの形式が正しくなければその日のログを初期化する
                    #     cur.execute('DELETE FROM log WHERE ID=%s AND date=%s', (stay_id, today))
                    #     conn.commit()

        # logテーブルの今日のログが0個なら、送られてきたデータをそのまま追加する
        else:
            if len(receive_members) > 0:
                for member in receive_members:
                    cur.execute("INSERT INTO log (date, ID, period, room, rssi) VALUES (%s, %s, %s, %s, %s)", (
                        today, member['id'], time + "~", receive_room, member['rssi']))
                    conn.commit()

            # 1日前の日付を取得
            yesterday = str((datetime.today() - timedelta(days=1)).date())

            # 処理フラグのチェック(その日に一度も実行していないなら空の値が返ってくる)
            cur.execute(
                "SELECT * FROM `maintenance` WHERE date=%s", (yesterday, ))

            # 泊まっていた人向けの処理(日をまたいでしまうとperiodの最後のデータが「~」のままになってしまう問題を修正する)
            if len(cur.fetchall()) == 0:
                # 前日の滞在履歴(IDとperiod)を取得
                cur.execute("SELECT ID, period FROM log WHERE date BETWEEN %s AND %s",
                            (yesterday + " 00:00:00", yesterday + " 23:59:59"))
                logs = cur.fetchall()
                # periodの最後のデータが「~」で終わっているデータを探して一番後ろに23:59:59を入れる
                fix_datas = []
                for log in logs:
                    if log[1].split(',')[-1] != '':
                        fix_datas.append(
                            {'id': log[0], 'data': log[1]+'23:59:59,'})

                # データベースに処理を反映する
                for data in fix_datas:
                    cur.execute('UPDATE log SET period=%s WHERE ID=%s AND date=%s',
                                (data['data'], data['id'], yesterday))
                    conn.commit()
                    # 該当IDのroomカラムを空にし、rssiを0にし、flagを0にする(退出処理)
                    cur.execute(
                        'UPDATE now SET room=%s, rssi=%s, flag=%s WHERE ID=%s', ('', 0, 0, data['id']))
                    conn.commit()

                # 処理をしたフラグを立てる
                cur.execute(
                    "INSERT INTO `maintenance`(`date`, `formatCheck`) VALUES (%s,1)", (yesterday, ))
                conn.commit()

        # データベースとの接続を解除
        conn.close()

        # return '({}, {})'.format(str(member[0]['rssi']), room)
        return jsonify({'res': 'Data Receive Ok!'})

    else:
        abort(500, 'データベースのアップデートはPOSTで行なってください。')
        return jsonify({'message': 'Error'})


# 在室者を返す
@app.route('/stay')
def get_stay():
    # データベースに接続
    conn = connect_db()
    cur = conn.cursor()

    # nowテーブル内のflagが1のID情報を取得
    cur.execute(
        'SELECT ID.ID, ID.name, ID.team, now.room FROM ID JOIN now ON ID.ID = now.ID AND now.flag=1 AND ID.operable=1')
    datas = cur.fetchall()

    # JSONを作成
    keys = ['ID', 'name', 'team', 'room']  # JSONのキー
    return_json = make_return_dict(keys, datas)

    # データベースとの接続を解除
    conn.close()

    return jsonify(return_json)


# 最後に滞在を確認できた時間を返す関数
@app.route('/last-time')
def get_last_time():
    # データベースに接続
    conn = connect_db()
    cur = conn.cursor()

    # 最終滞在時間の情報取得
    cur.execute('SELECT ID.ID, ID.name, ID.team, date_format(now.datetime,"%Y-%m-%d %H:%i:%S") FROM ID JOIN now ON ID.ID = now.ID AND ID.operable=1')
    datas = cur.fetchall()

    # JSONを作成
    keys = ['ID', 'name', 'team', 'lastTime']  # JSONのキー
    return_json = make_return_dict(keys, datas)

    # データベースとの接続を解除
    conn.close()

    return jsonify(return_json)


# 日付を基にログデータを返す関数
@app.route('/log')
def get_log():

    # GETパラメータを取得
    date1 = request.args.get('date1', default="None")
    date2 = request.args.get('date2', default="None")
    mode = request.args.get('mode', default="None")

    # データベース接続処理
    conn = connect_db()
    cur = conn.cursor()

    # パラメータが指定されていない時(今日のログだけを返す)
    if date1 == 'None' and date2 == 'None':
        # 今日の日付けを取得
        today = str(date.today())
        # クエリ
        cur.execute("SELECT log.ID, ID.name, ID.team, date_format(log.date,'%Y-%m-%d'), log.period, log.room, log.rssi FROM log JOIN ID ON log.ID = ID.ID AND log.date BETWEEN %s AND %s",
                    (today + ' 00:00:00', today + ' 23:59:59'))
        logs = cur.fetchall()
        # データベースとの接続を解除
        conn.close()

    # パラメータが片方しか設定されていない時
    elif date1 == 'None' or date2 == 'None':
        abort(500, '不正なパラメータが入力されました。')

    # パラメータが指定されている時
    else:
        # クエリ
        cur.execute("SELECT log.ID, ID.name, ID.team, date_format(log.date,'%Y-%m-%d'), log.period, log.room, log.rssi FROM log JOIN ID ON log.ID = ID.ID AND log.date BETWEEN %s AND %s",
                    (date1 + ' 00:00:00', date2 + ' 23:59:59'))
        logs = cur.fetchall()
        # データベースとの接続を解除
        conn.close()

    # 返却するデータを辞書型で作成
    keys = ['ID', 'name', 'team', 'date', 'period', 'room', 'rssi']
    return_json = make_return_dict(keys, logs)  # JSONのキー

    # GETのmdoeオプションに"web"モードが指定されていた時
    if mode == 'web':
        # periodのデータ(カンマ区切りの時間の文字列)に改行タグ(<br>)を入れる
        for i in range(len(return_json)):
            return_json[i]['period'] = make_web_format(
                return_json[i]['period'])
            return_json[i]['room'] = make_web_format(return_json[i]['room'])

    # GETのmodeオプションに何も指定されていない時
    else:
        # periodのデータ(カンマ区切りの時間の文字列)を辞書型のリストに変換する
        for i in range(len(return_json)):
            try:
                return_json[i]['period'] = make_period_dict(
                    return_json[i]['period'])
            except:
                pass

    return jsonify(return_json)


# 日付を基にログデータを返す関数
@app.route('/log-time')
def get_log_time():

    # GETパラメータを取得
    yearmonth = request.args.get('month', default="None")

    # 今日の日付を取得 (例:2019-02-04)
    today = str(date.today())

    # データベース接続処理
    conn = connect_db()
    cur = conn.cursor()

    # 月が指定されていた時の処理
    if yearmonth != "None":
        # その月の1日の00:00:00から31日の23:59:59までのデータを検索
        cur.execute("SELECT log.ID, ID.name, log.period FROM log JOIN ID ON log.ID = ID.ID AND log.date BETWEEN %s AND %s AND ID.operable=1",
                    (yearmonth + '-01 00:00:00', yearmonth + '-31 23:59:59'))

    # 月が指定されていない時
    else:
        # 全期間の累計在室時間を計算する
        cur.execute("SELECT log.ID, ID.name, log.period FROM log JOIN ID ON log.ID = ID.ID AND log.date BETWEEN %s AND %s AND ID.operable=1",
                    ('2020-10-11 00:00:00', today + ' 23:59:59'))

    logs = cur.fetchall()   # クエリを実行する
    users_dict = {}

    # 受け取ったデータから総合滞在時間を計算し、辞書型にしてリストに格納する
    for log in logs:
        # もし、users_dict内に同じIDのデータがなければデータを追加する
        if log[0] not in users_dict:
            users_dict[log[0]] = {
                'ID': log[0], 'name': log[1], 'total_time': calc_total_time(log[2])}

        # もし、users_dict内に同じIDがあれば時間を加算して更新
        else:
            tmp_t = users_dict[log[0]]['total_time']
            users_dict[log[0]]['total_time'] = tmp_t + calc_total_time(log[2])

    # users_dictをそのまま送ると
    # "e7d61ea3f8dd49c88f2ff2484c07acb9-36624-25369"{
    # "ID": "e7d61ea3f8dd49c88f2ff2484c07acb9-36624-25369",
    # "name": "takizawa",
    # "total_time": 0}
    # 上記の用にIDが2回出てしまうので以下の処理で体裁を整える
    return_datas = []
    for key in users_dict.keys():
        return_datas.append(users_dict[key])

    # データベースとの接続を解除
    conn.close()

    return jsonify(return_datas)


# 同時に入室している人のログを返す関数
@app.route('/log-group')
def get_log_group():
    # GETパラメータを取得
    date1 = request.args.get('date1', default="None")
    date2 = request.args.get('date2', default="None")

    # データベース接続処理
    conn = connect_db()
    cur = conn.cursor()

    # パラメータが指定されていない時(今日のログだけを返す)
    if date1 == 'None' and date2 == 'None':
        # 今日の日付けを取得
        today = str(date.today())
        # クエリ
        cur.execute("SELECT date_format(date,'%Y-%m-%d'), date_format(entryTime,'%Y-%m-%d %H:%i:%S'), date_format(exitTime,'%Y-%m-%d %H:%i:%S'), ids FROM groupEntryLog WHERE date BETWEEN %s AND %s",
                    (today + ' 00:00:00', today + ' 23:59:59'))
        logs = cur.fetchall()

    # パラメータが片方しか設定されていない時
    elif date1 == 'None' or date2 == 'None':
        abort(500, '不正なパラメータが入力されました。')

    # パラメータが指定されている時
    else:
        # クエリ
        cur.execute("SELECT date_format(date,'%Y-%m-%d'), date_format(entryTime,'%Y-%m-%d %H:%i:%S'), date_format(exitTime,'%Y-%m-%d %H:%i:%S'), ids FROM groupEntryLog WHERE date BETWEEN %s AND %s",
                    (date1 + ' 00:00:00', date2 + ' 23:59:59'))
        logs = cur.fetchall()

    logs_list = []
    # logsの中身はタプルなのでlistに変換する
    for i in logs:
        logs_list.append(list(i))

    # 取得したデータのうち、IDデータを名前に変換
    for i in range(len(logs_list)):
        logs_list[i][3] = ID_to_name(cur, logs_list[i][3])

    # 返却するデータを辞書型で作成
    keys = ['date', 'startOfPeriod', 'endOfPeriod', 'names']
    return_json = make_return_dict(keys, logs_list)  # JSONのキー

    # データベースとの接続を解除
    conn.close()

    return jsonify(return_json)


if __name__ == "__main__":
    app.run(debug=True)


# conn = mydb.connect(host='mysql57.kajilab.sakura.ne.jp',
#                     port='3306',
#                     user='kajilab',
#                     password='kaj1labkaj1lab',
#                     database='kajilab_staywatch')

# conn.ping(reconnect = True)
# print(conn.is_connected())
# cur = conn.cursor()

# import io, sys
# sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
