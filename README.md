# stay-watch-reciever

BLEビーコンを受信してサーバにデータを送るRaspberry Pi用のプログラムです。

## 構成

```sh
stay_watch/        Python パッケージ本体 (config / db / beacon / scanner / poster / cli)
systemd/           systemd unit ファイル (scan/post の service と timer)
scripts/install.sh セットアップスクリプト
```

実行はsystemd timerによって2系統で制御されます。

| Timer | 周期 | 内容 |
| --- | --- | --- |
| `stay-watch-scan.timer` | 70 秒間隔 | `python -m stay_watch scan -t 60` で BLE スキャン → DB 蓄積 |
| `stay-watch-post.timer` | 5 分間隔 | `python -m stay_watch post` で集計 → サーバ POST、その後 `hciconfig hci0 down/up` |

## セットアップ (Raspberry Pi)

```bash
cp .env.example .env
$EDITOR .env                 # ROOM_ID と STAYWATCH_API_KEY を設定
./scripts/install.sh         # apt + .venv + 依存 install + systemd unit 配置 + timer 起動
```

`install.sh` は以下を自動で実行します:

1. apt で `python3-venv` / `build-essential` / `libglib2.0-dev` / `pkg-config` を導入 (bluepy のビルドに必要)
2. `./.venv` を作成し `requirements.txt` を pip install
3. `systemd/*.service` の `__REPO_DIR__` を実際のリポジトリ絶対パスに sed 置換しつつ `/etc/systemd/system/` へ配置 (`/home/pi` 以外のユーザでも動作)
4. `daemon-reload` + scan / post の両 timer を `enable --now`

## 手動操作

```bash
.venv/bin/python -m stay_watch init    # DB 初期化
.venv/bin/python -m stay_watch scan    # 1 回スキャン
.venv/bin/python -m stay_watch post    # 集計 + POST + DB クリア
.venv/bin/python -m stay_watch clear   # DB のみクリア
```

## systemd 操作 (Makefile)

```bash
make status     # timer の状態確認
make start      # timer 起動
make stop       # timer 停止
make restart    # timer 再起動
make enable     # 自動起動有効化
make disable    # 自動起動無効化
make list       # timer 一覧
make logs       # service ログを tail
```
