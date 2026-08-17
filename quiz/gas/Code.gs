/**
 * スプレッドシートに紐づけて使う、アンケートの配信＋記録スクリプト。
 *
 * これ1つで次の2つを兼ねます。
 *   - ログイン不要で開けるWebページとしてアンケートを配信する（doGet）
 *   - 回答をこのスプレッドシートに1行ずつ記録する（saveAnswers）
 *
 * ■ 設置手順
 *   1. Googleスプレッドシートを新規作成する
 *   2. 拡張機能 → Apps Script を開く
 *   3. 既定の「コード.gs」の中身を全部消して、このファイルの中身を貼り付ける
 *   4. 左の「ファイル」の＋ → HTML を選び、名前を index にして
 *      gas/index.html の中身を貼り付ける（拡張子 .html は自動で付く）
 *   5. 右上「デプロイ」→「新しいデプロイ」→ 歯車から「ウェブアプリ」を選ぶ
 *        説明          : なんでもよい
 *        次のユーザーとして実行 : 自分
 *        アクセスできるユーザー : 全員          ← ここが「ログイン不要」の鍵
 *   6. 「デプロイ」を押し、初回は表示される認可画面を承認する
 *   7. 表示される「ウェブアプリのURL」がアンケートのURL
 *        https://script.google.com/macros/s/..../exec
 *
 * このURLを送れば、相手はGoogleにもClaudeにもログインせず回答できます。
 * 回答が終わった時点で、このスプレッドシートに自動で1行追加されます。
 *
 * ■ 質問を変えたとき
 *   index.html を貼り替えたあと、「デプロイ」→「デプロイを管理」→ 鉛筆アイコン →
 *   バージョンを「新バージョン」にして更新すると、URLは変わらず中身が差し替わります。
 */

var SHEET_NAME = '回答';

function doGet() {
  return HtmlService.createHtmlOutputFromFile('index')
    .setTitle('あなたのこと、もう少し知りたい。')
    .addMetaTag('viewport', 'width=device-width, initial-scale=1');
}

/**
 * ブラウザ側から google.script.run で呼ばれる。
 * payload = { text: '整形済みの全文', data: { answers: [...], optional: {...} } }
 */
function saveAnswers(payload) {
  var lock = LockService.getScriptLock();
  lock.waitLock(20000);
  try {
    var data = payload.data;
    var sheet = getSheet_();

    var header = ['受信日時'];
    var row = [new Date()];

    data.answers.forEach(function (a) {
      header.push(a.id + ' ' + a.question);
      row.push(a.selected === null ? '' : a.selected);
    });
    header.push('任意 ' + data.optional.question);
    row.push(data.optional.answer || '');

    // 見出しが無い、または質問が変わっていたら見出しを入れ直す
    var current = sheet.getLastRow() === 0
      ? []
      : sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];

    if (current.join('') !== header.join('')) {
      if (sheet.getLastRow() > 0) {
        sheet = SpreadsheetApp.getActiveSpreadsheet().insertSheet(
          SHEET_NAME + ' ' + Utilities.formatDate(new Date(), 'JST', 'yyyyMMdd-HHmm')
        );
      }
      sheet.appendRow(header);
      sheet.setFrozenRows(1);
    }

    sheet.appendRow(row);
    return 'ok';
  } finally {
    lock.releaseLock();
  }
}

function getSheet_() {
  var book = SpreadsheetApp.getActiveSpreadsheet();
  return book.getSheetByName(SHEET_NAME) || book.insertSheet(SHEET_NAME);
}
