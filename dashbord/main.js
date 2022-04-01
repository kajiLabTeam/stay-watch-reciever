var circle_data;    // ロードメッセージのDOM要素を入れる変数
var timer;          // タイマーの定義
const reloadTime = 10000;   // リロードする時間間隔


function isSmartPhone() {
    if (navigator.userAgent.match(/iPhone|Android.+Mobile/)) {
        return true;
    } else {
        return false;
    }
}


// 滞在ウォッチからデータを取得する関数
function getJsonData(url, tableName, retMessage) {
    // url: 送信先のURL
    // tableName: 取得したJSONデータを表示する表のID名
    // retMessage: JSONデータが空だった時に表示するメッセージ

    // デバック用
    // $("#span1").text("データ取得中です");

    // 1. $.getJSONメソッドで通信を行う
    $.getJSON(url)

        // 2. doneは、通信に成功した時に実行される
        //  引数のretrunDataは、通信で取得したデータ
        .done(function (retrunData, textStatus, jqXHR) {
            // デバック用
            // $("#span1").text(jqXHR.status); //例：200
            // $("#span2").text(textStatus); //例：success
            // 3. キーを指定して値を表示
            // $("#span3").text(retrunData[0]["ID"]);
            // console.log(Object.keys(retrunData).length);
            // 4. JavaScriptオブジェクトをJSONに変換してコンソールに表示
            console.log(JSON.stringify(retrunData));
            console.log('Data Get Success!');

            // 表を初期化
            $(tableName).bootstrapTable('destroy');

            // 受信したデータを表に描画
            $(tableName).bootstrapTable({
                data: retrunData,
                // JSONデータの中身が空だった時のメッセージ
                formatNoMatches: function () {
                    return retMessage;
                }
            });

            // ローディングメッセージを削除する
            $(".loading-wrap").remove();
            circle_data = $('#circle').detach();

            // デーらの受信が完了してから0.5秒後にメッセージを消す
            // setTimeout(
            //     function () {
            //         // ロード完了メッセージを削除する
            //         $(".loading-wrap").remove();
            //     },
            //     "500"
            // );
        })

        // 5. failは、通信に失敗した時に実行される
        .fail(function (jqXHR, textStatus, errorThrown) {
            // デバック用
            // $("#span1").text(jqXHR.status); //例：404
            // $("#span2").text(textStatus);  //例：error
            // $("#span3").text(errorThrown); //例：NOT FOUND
            console.log(jqXHR.status);
            console.log(textStatus);
            console.log(errorThrown);

            // 通信が失敗した時にリトライする
            if (jqXHR.status == 0) {
                getJsonData(url, tableName, retMessage);
                console.log('Retry!');
            }
        })

        // 6. alwaysは、成功/失敗に関わらず実行される
        .always(function () {
            // デバック用
            // $("#span4").text("完了しました");
        });
}


// 在室履歴のボタンをクリックした時の処理
$(function () {
    $(".nav li a").on("click", function () {
        if (this.id == 'log') {
            
            // ローディングメッセージを表示
            circle_data.prependTo('#circle2');

            // 送信先のURL
            const url        = "https://kajilab.net/stay-watch/log?mode=web";
            const tableName  = '#logTable';
            const retMessage = '在室履歴はありません。';

            // 滞在ウォッチから在室者の履歴を取得する
            getJsonData(url, tableName, retMessage);

            clearInterval(timer);   // 2回目以降の実行時はタイマーを再設定する
            timer = setInterval(function () {
                getJsonData(url, tableName, retMessage);
            }, reloadTime);
        }
    });
});


// 在室者のボタンをクリックした時の処理
$(function () {
    $(".nav li a").on("click", function () {
        if (this.id == 'stay') {

            // ローディングメッセージを表示
            circle_data.prependTo('#circle2');

            // 送信先のURL
            const url = "https://kajilab.net/stay-watch/stay";
            const tableName = '#stayTable';
            const retMessage = '現在、在室者はいません。';

            // 滞在ウォッチから在室者の履歴を取得する
            getJsonData(url, tableName, retMessage);

            clearInterval(timer);   // 2回目以降の実行時はタイマーを再設定する
            timer = setInterval(function () {
                getJsonData(url, tableName, retMessage);
            }, reloadTime);
        }
    });
});

// 利用者一覧のボタンをクリックした時の処理
$(function () {
    $(".nav li a").on("click", function () {
        if (this.id == 'info') {

            // ローディングメッセージを表示
            circle_data.prependTo('#circle2');

            // 送信先のURL
            const url = "https://kajilab.net/stay-watch/userInfo";
            const tableName = '#userTable';
            const retMessage = '現在、在室者はいません。';

            // 滞在ウォッチから在室者の履歴を取得する
            getJsonData(url, tableName, retMessage);

            clearInterval(timer);   // 2回目以降の実行時はタイマーを再設定する
            timer = setInterval(function () {
                getJsonData(url, tableName, retMessage);
            }, reloadTime);
        }
    });
});

// 滞在ウォッチから在室者のJSONを取得する
$(function () {
    // 送信先のURL
    const url        = "https://kajilab.net/stay-watch/stay";
    const tableName  = '#stayTable';
    const retMessage = '現在、在室者はいません。';

    // 滞在ウォッチから在室者のJSONを取得する
    getJsonData(url, tableName, retMessage);
    timer = setInterval(function () {
        getJsonData(url, tableName, retMessage);
    }, reloadTime);
});

// 滞在ウォッチから在室者のJSONを取得する
$(function () {
    // 送信先のURL
    const url        = "https://kajilab.net/stay-watch/userInfo";
    const tableName  = '#userTable';
    const retMessage = '現在、在室者はいません。';

    // 滞在ウォッチから在室者のJSONを取得する
    getJsonData(url, tableName, retMessage);
    timer = setInterval(function () {
        getJsonData(url, tableName, retMessage);
    }, reloadTime);
});