/**
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

var QUESTIONS = [
  {
    "id": "Q1",
    "scene": [
      "友達との旅行。"
    ],
    "ask": "予定を決めるなら一番近いのは？",
    "options": [
      "行く場所や時間まである程度決めておきたい",
      "メインだけ決めて、あとはその場で",
      "候補だけいくつか用意しておく",
      "当日の気分で決めるのが好き"
    ]
  },
  {
    "id": "Q2",
    "scene": [
      "ちょっと嫌なことがあった日に恋人と会いました。"
    ],
    "ask": "一番嬉しいのは？",
    "options": [
      "「なんかあった？」と気づいてくれる",
      "自分から話したらじっくり聞いてくれる",
      "美味しいものや楽しいことで気分転換してくれる",
      "特に触れず、いつも通り接してくれる"
    ]
  },
  {
    "id": "Q3",
    "scene": [
      "何気なく「これちょっと欲しいかも」と話したものを、数か月後に恋人が覚えていました。"
    ],
    "ask": "どう感じる？",
    "options": [
      "めちゃくちゃ嬉しい",
      "結構嬉しい",
      "嬉しいけど、そこまで重要ではない",
      "あまり何とも思わない"
    ]
  },
  {
    "id": "Q4",
    "scene": [
      "楽しみにしていたデートの日。",
      "恋人から突然、",
      "「ごめん、今日予定変えてもいい？」",
      "と言われました。"
    ],
    "ask": "最初に感じるものに一番近いのは？",
    "options": [
      "理由が気になる",
      "ちょっと残念・悲しい",
      "仕方ないと思う",
      "新しい予定も楽しそうなら全然OK",
      "自分との予定を大事にしてほしかったと思う"
    ]
  },
  {
    "id": "Q5",
    "scene": [
      "恋人と意見が完全に食い違いました。"
    ],
    "ask": "自分に一番近いのは？",
    "options": [
      "納得できるまで話したい",
      "お互いの考えを聞いて落とし所を探したい",
      "一旦時間を置いてから話したい",
      "大きな問題じゃなければ自分が折れてもいい",
      "喧嘩になるくらいなら流したい"
    ]
  },
  {
    "id": "Q6",
    "scene": [
      "自分が落ち込んでいる時に恋人から、",
      "「じゃあこうすれば解決できるんじゃない？」",
      "と言われました。"
    ],
    "ask": "一番近い感覚は？",
    "options": [
      "解決策を考えてくれるのは嬉しい",
      "まず気持ちを分かってから言ってほしい",
      "正しいことを言われても今は違うと思う",
      "内容による",
      "自分で解決したいのであまり介入してほしくない"
    ]
  },
  {
    "id": "Q7",
    "scene": [
      "恋人から突然、",
      "「今からちょっと出かけない？」",
      "と誘われました。"
    ],
    "ask": "予定が空いていたら？",
    "options": [
      "面白そう、すぐ行く",
      "行き先を聞いてから決める",
      "少し準備する時間がほしい",
      "急な予定変更はあまり好きじゃない"
    ]
  },
  {
    "id": "Q8",
    "scene": [
      "恋人が友達と遊んでいて、数時間連絡がありません。"
    ],
    "ask": "一番近いのは？",
    "options": [
      "楽しんでるんだろうし全然気にならない",
      "少し気になるけど特に連絡はしない",
      "何してるかなとは結構気になる",
      "一言くらい連絡があると嬉しい",
      "誰といるかによってかなり変わる"
    ]
  },
  {
    "id": "Q9",
    "scene": [
      "恋人があなたの髪型や服の小さな変化に気づきませんでした。"
    ],
    "ask": "どう感じる？",
    "options": [
      "全然気にならない",
      "気づいたら嬉しかったな、くらい",
      "ちょっと残念",
      "結構気づいてほしい",
      "変化の内容による"
    ]
  },
  {
    "id": "Q10",
    "scene": [],
    "ask": "恋人から褒められるなら、どれが一番嬉しい？",
    "options": [
      "「今日かわいい」",
      "「一緒にいると楽しい」",
      "「そういうところ優しいよね」",
      "「頑張ってるのちゃんと知ってるよ」",
      "自分でも気づいていないような部分を具体的に褒められる"
    ]
  },
  {
    "id": "Q11",
    "scene": [
      "ちょっと空気が悪くなった時、恋人が笑わせようとしてきました。"
    ],
    "ask": "一番近いのは？",
    "options": [
      "割とすぐ笑って許してしまう",
      "面白ければちょっと機嫌が直る",
      "まずちゃんと話してからにしてほしい",
      "今ふざけるところじゃないと思う",
      "原因による"
    ]
  },
  {
    "id": "Q12",
    "scene": [
      "恋人が異性の友達と二人で食事に行くことになりました。"
    ],
    "ask": "一番近い感覚は？",
    "options": [
      "特に気にならない",
      "事前に教えてくれれば大丈夫",
      "相手が誰なのかは気になる",
      "正直ちょっと嫌",
      "二人きりは嫌"
    ]
  },
  {
    "id": "Q13",
    "scene": [
      "忙しい一週間。"
    ],
    "ask": "恋人とあまり会えないとしたら、どれが一番嬉しい？",
    "options": [
      "短時間でも会う",
      "電話する",
      "LINEなどでこまめに話す",
      "「落ち着いたら会おう」と予定だけ決める",
      "忙しい時はお互い自分のことに集中する"
    ]
  },
  {
    "id": "Q14",
    "scene": [],
    "ask": "誕生日に恋人が何かしてくれるなら？",
    "options": [
      "自分が欲しいと言っていたものを覚えていてくれる",
      "相手が自分で一生懸命考えてくれる",
      "サプライズしてくれる",
      "一緒にどこかへ行って思い出を作る",
      "特別なことより、一緒にゆっくり過ごしたい"
    ]
  },
  {
    "id": "Q15",
    "scene": [],
    "ask": "恋人との関係で、一番「幸せだな」と感じそうなのは？",
    "options": [
      "何でも話せて理解し合えている",
      "一緒にたくさん笑っている",
      "大切にされていると実感できる",
      "お互いを信頼して自由でいられる",
      "困った時に支え合える",
      "一緒にいるだけで安心できる"
    ]
  }
];

var OPTIONAL_QUESTION = {
  "lead": "最後にひとつだけ。",
  "ask": "自分の性格で「ここ、ちょっと面倒かも（笑）」と思うところがあれば教えて。",
  "placeholder": "思いつかなければ、そのまま次へ進んでOK。",
  "note": "書いても書かなくても大丈夫です。"
};

var MILESTONES = {
  "5": "いい感じ。あと10問。",
  "10": "あと5問。"
};

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
  ].join('\n');

  Logger.log(lines);
  return lines;
}

/** 状況説明と質問文を1つのタイトルにまとめる */
function titleOf_(q) {
  var scene = (q.scene || []).join('');
  return scene ? scene + '\n' + q.ask : q.ask;
}

/** 使えない設定は黙って飛ばす */
function trySet_(fn) {
  try { fn(); } catch (e) { /* このアカウントでは指定できない設定 */ }
}
