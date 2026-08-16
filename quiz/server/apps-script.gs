/**
 * 回答をスプレッドシートに1行ずつ記録する受け口（Google Apps Script）。
 *
 * ■ 設置手順
 *   1. Googleスプレッドシートを新規作成する
 *   2. 拡張機能 → Apps Script を開き、このファイルの中身を貼り付けて保存
 *   3. 右上「デプロイ」→「新しいデプロイ」→ 種類は「ウェブアプリ」
 *        - 次のユーザーとして実行: 自分
 *        - アクセスできるユーザー: 全員
 *   4. 表示された URL（https://script.google.com/macros/s/..../exec）をコピー
 *   5. quiz/config.js を次のように書き換える
 *
 *        const SUBMIT_CONFIG = {
 *          mode: 'endpoint',
 *          endpoint: 'ここにコピーしたURL',
 *          formName: 'quiz-answers'
 *        };
 *
 * 回答があるたびに、1行 = 1人分として追記されます。
 * 質問文が変わった場合は、新しい見出し行を持つシートが自動で作られます。
 */

function doPost(e) {
  var body = JSON.parse(e.postData.contents);
  var data = body.data;              // { answers: [...], optional: {...} }
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheets()[0];

  var header = ['受信日時'];
  var row = [new Date()];

  data.answers.forEach(function (a) {
    header.push(a.id + ' ' + a.question);
    row.push(a.selected === null ? '' : a.selected);
  });
  header.push('任意 ' + data.optional.question);
  row.push(data.optional.answer || '');

  // 1行目が空、または質問が変わっている場合は見出しを入れ直す
  var firstRow = sheet.getLastRow() === 0
    ? []
    : sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];

  if (firstRow.join('') !== header.join('')) {
    if (sheet.getLastRow() > 0) {
      sheet = SpreadsheetApp.getActiveSpreadsheet()
        .insertSheet('回答 ' + Utilities.formatDate(new Date(), 'JST', 'yyyyMMdd-HHmm'));
    }
    sheet.appendRow(header);
    sheet.setFrozenRows(1);
  }

  sheet.appendRow(row);

  return ContentService
    .createTextOutput(JSON.stringify({ ok: true }))
    .setMimeType(ContentService.MimeType.JSON);
}

function doGet() {
  return ContentService.createTextOutput('ok');
}
