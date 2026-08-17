#!/usr/bin/env node
/**
 * questions.js から Googleフォーム生成スクリプト（gas/CreateForm.gs）を作る。
 *
 *   node quiz/gas/build-createform.js
 *
 * 質問文を手で写し替えると必ずズレるので、必ずこれで生成すること。
 * 生成後に、埋め込まれた内容が questions.js と一致するか自己検査する。
 */

const fs = require('fs');
const path = require('path');
const vm = require('vm');

const QUIZ_DIR = path.resolve(__dirname, '..');
const OUT = path.join(__dirname, 'CreateForm.gs');

// questions.js を読み込む（const 宣言をそのまま評価して取り出す）
const sandbox = {};
vm.createContext(sandbox);
vm.runInContext(
  fs.readFileSync(path.join(QUIZ_DIR, 'questions.js'), 'utf8') +
  ';this.__out = { QUESTIONS, OPTIONAL_QUESTION, MILESTONES };',
  sandbox
);
const { QUESTIONS, OPTIONAL_QUESTION, MILESTONES } = sandbox.__out;

const header = `/**
 * 15問のアンケートを「Googleフォーム」として自動生成するスクリプト。
 *
 * ■ 使い方（4ステップ）
 *   1. https://script.google.com/home/projects/create を開く
 *   2. 表示されたエディタの中身を全部消して、このファイルの中身を貼り付けて保存
 *   3. 上部の関数名が createQuiz になっているのを確認して「実行」
 *      （初回だけ承認画面が出るので許可する）
 *   4. 下に出る「実行ログ」に3つのURLが表示される
 *        回答用URL   … これを相手に送る（ログイン不要で開ける）
 *        回答一覧     … 回答がたまるスプレッドシート
 *        フォーム編集 … あとから質問を直す用
 *
 * ■ このファイルは生成物
 *   quiz/questions.js を直したら、次のコマンドで作り直す。
 *     node quiz/gas/build-createform.js
 */

// true にすると1問ずつページを分けて表示する（進捗バーも出る）
var ONE_QUESTION_PER_PAGE = true;

var FORM_TITLE = 'あなたのこと、もう少し知りたい。';
var FORM_DESCRIPTION = '15問・約2分。直感で選んでね。';
var THANKS_MESSAGE = 'ありがとう。おつかれさま。';

var QUESTIONS = ${JSON.stringify(QUESTIONS, null, 2)};

var OPTIONAL_QUESTION = ${JSON.stringify(OPTIONAL_QUESTION, null, 2)};

var MILESTONES = ${JSON.stringify(MILESTONES, null, 2)};
`;

const body = `
function createQuiz() {
  var form = FormApp.create(FORM_TITLE);
  form.setDescription(FORM_DESCRIPTION);
  form.setProgressBar(ONE_QUESTION_PER_PAGE);
  form.setShowLinkToRespondAgain(false);
  form.setConfirmationMessage(THANKS_MESSAGE);

  // 相手にログインを求めない設定。個人アカウントでは指定できないので個別に試す
  trySet_(function () { form.setCollectEmail(false); });
  trySet_(function () { form.setLimitOneResponsePerUser(false); });
  trySet_(function () { form.setRequireLogin(false); });

  QUESTIONS.forEach(function (q, i) {
    if (ONE_QUESTION_PER_PAGE && i > 0) {
      var page = form.addPageBreakItem();
      var milestone = MILESTONES[String(i + 1)];
      if (milestone) page.setTitle(milestone);
    }
    form.addMultipleChoiceItem()
      .setTitle(titleOf_(q))
      .setChoiceValues(q.options)
      .setRequired(true);
  });

  // 最後の任意質問
  if (ONE_QUESTION_PER_PAGE) {
    form.addPageBreakItem().setTitle(OPTIONAL_QUESTION.lead);
  }
  form.addParagraphTextItem()
    .setTitle(OPTIONAL_QUESTION.ask)
    .setHelpText(OPTIONAL_QUESTION.note)
    .setRequired(false);

  // 回答をスプレッドシートにためる
  var book = SpreadsheetApp.create(FORM_TITLE + '（回答）');
  form.setDestination(FormApp.DestinationType.SPREADSHEET, book.getId());

  var lines = [
    '',
    '========================================',
    '回答用URL（これを送る）: ' + form.getPublishedUrl(),
    '回答一覧              : ' + book.getUrl(),
    'フォーム編集          : ' + form.getEditUrl(),
    '========================================'
  ].join('\\n');

  Logger.log(lines);
  return lines;
}

/** 状況説明と質問文を1つのタイトルにまとめる */
function titleOf_(q) {
  var scene = (q.scene || []).join('');
  return scene ? scene + '\\n' + q.ask : q.ask;
}

/** 使えない設定は黙って飛ばす */
function trySet_(fn) {
  try { fn(); } catch (e) { /* このアカウントでは指定できない設定 */ }
}
`;

fs.writeFileSync(OUT, header + body, 'utf8');

// --- 自己検査: 生成物を実際に評価して questions.js と一致するか確かめる ----
// （評価が通ること自体が構文チェックにもなる）
const gasBox = { Logger: { log() {} } };
vm.createContext(gasBox);
vm.runInContext(
  fs.readFileSync(OUT, 'utf8') +
  ';this.__check = { QUESTIONS, OPTIONAL_QUESTION, MILESTONES, titleOf_, createQuiz };',
  gasBox
);
const got = gasBox.__check;

const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const checks = [
  ['生成物が有効なJSとして評価できる', typeof got.createQuiz === 'function'],
  ['問題数が15', got.QUESTIONS.length === 15],
  ['質問データが完全一致', same(got.QUESTIONS, QUESTIONS)],
  ['任意質問が一致', same(got.OPTIONAL_QUESTION, OPTIONAL_QUESTION)],
  ['途中の一言が一致', same(got.MILESTONES, MILESTONES)],
  ['選択肢の総数が一致', got.QUESTIONS.reduce((n, q) => n + q.options.length, 0) ===
                        QUESTIONS.reduce((n, q) => n + q.options.length, 0)],
  ['状況説明つきの見出しが正しい',
    got.titleOf_(QUESTIONS[1]) === 'ちょっと嫌なことがあった日に恋人と会いました。\n一番嬉しいのは？'],
  ['状況説明なしの見出しが正しい',
    got.titleOf_(QUESTIONS[9]) === '恋人から褒められるなら、どれが一番嬉しい？']
];

let failed = 0;
checks.forEach(([name, ok]) => {
  if (!ok) failed++;
  console.log((ok ? 'PASS ' : 'FAIL ') + name);
});
console.log('wrote ' + OUT + ' (' + (fs.statSync(OUT).size / 1024).toFixed(1) + ' KB)');
process.exit(failed ? 1 : 0);
