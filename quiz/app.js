/* =========================================================
   状態管理
   - 回答は localStorage にだけ保存する（外部送信はしない）
   - アプリ側では回答の判定・分類・ラベル付けは一切行わない
   ========================================================= */

const STORAGE_KEY = 'love-quiz.state.v3';
const SCHEMA_VERSION = 3;

/* 旧バージョンの保存データ（50問版 / 旧15問版）は読み込まずに破棄する */
const LEGACY_KEYS = [
  'love-quiz.state',
  'love-quiz.state.v1',
  'love-quiz.state.v2',
  'personality-quiz-state',
  'quizAnswers'
];

const AUTO_ADVANCE_MS = 420;

function emptyState() {
  return {
    v: SCHEMA_VERSION,
    answers: new Array(QUESTIONS.length).fill(null), // 各要素は選択肢のindex
    free: '',
    index: 0,
    completed: false,
    startedAt: null,
    updatedAt: null
  };
}

let state = emptyState();

function loadState() {
  try {
    LEGACY_KEYS.forEach(function (k) { localStorage.removeItem(k); });
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!parsed || parsed.v !== SCHEMA_VERSION) {
      localStorage.removeItem(STORAGE_KEY);
      return null;
    }
    if (!Array.isArray(parsed.answers) || parsed.answers.length !== QUESTIONS.length) {
      localStorage.removeItem(STORAGE_KEY);
      return null;
    }
    // 選択肢の数が変わっている場合は、その設問だけ無効にする
    parsed.answers = parsed.answers.map(function (a, i) {
      return (Number.isInteger(a) && a >= 0 && a < QUESTIONS[i].options.length) ? a : null;
    });
    parsed.free = typeof parsed.free === 'string' ? parsed.free : '';
    parsed.index = clamp(parsed.index || 0, 0, QUESTIONS.length - 1);
    parsed.completed = !!parsed.completed;
    return parsed;
  } catch (e) {
    return null;
  }
}

function saveState() {
  state.updatedAt = new Date().toISOString();
  if (!state.startedAt) state.startedAt = state.updatedAt;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch (e) {
    /* 保存できない環境でも回答自体は続けられるようにする */
  }
}

function clearState() {
  try { localStorage.removeItem(STORAGE_KEY); } catch (e) { /* noop */ }
}

function clamp(n, min, max) { return Math.min(Math.max(n, min), max); }

function answeredCount() {
  return state.answers.filter(function (a) { return a !== null; }).length;
}

/* =========================================================
   要素参照
   ========================================================= */
const el = {
  screens: {
    start: document.getElementById('screen-start'),
    quiz:  document.getElementById('screen-quiz'),
    free:  document.getElementById('screen-free'),
    done:  document.getElementById('screen-done')
  },
  resumeBox:   document.getElementById('resume-box'),
  resumeText:  document.getElementById('resume-text'),
  qwrap:       document.getElementById('qwrap'),
  milestone:   document.getElementById('milestone'),
  scene:       document.getElementById('q-scene'),
  ask:         document.getElementById('q-ask'),
  options:     document.getElementById('options'),
  back:        document.getElementById('btn-back'),
  fill:        document.getElementById('progress-fill'),
  count:       document.getElementById('progress-count'),
  freeLead:    document.getElementById('free-lead'),
  freeAsk:     document.getElementById('free-ask'),
  freeNote:    document.getElementById('free-note'),
  freetext:    document.getElementById('freetext'),
  preview:     document.getElementById('preview-text'),
  toast:       document.getElementById('toast')
};

/* =========================================================
   画面遷移
   ========================================================= */
let current = 'start';

function show(name) {
  current = name;
  Object.keys(el.screens).forEach(function (key) {
    el.screens[key].classList.toggle('is-active', key === name);
  });
  window.scrollTo({ top: 0, behavior: 'auto' });
}

/* =========================================================
   設問の描画
   ========================================================= */
let locked = false; // 自動送りの最中の二重タップ防止

function questionLabel(q) {
  return q.scene.join('') + q.ask;
}

function renderQuestion(animate) {
  const i = state.index;
  const q = QUESTIONS[i];

  // 進捗
  el.count.textContent = (i + 1) + ' / ' + QUESTIONS.length;
  el.fill.style.width = (((i + 1) / QUESTIONS.length) * 100) + '%';

  // 途中の一言
  const milestone = MILESTONES[i + 1];
  if (milestone) {
    el.milestone.textContent = milestone;
    el.milestone.hidden = false;
  } else {
    el.milestone.hidden = true;
  }

  // 質問文
  el.scene.innerHTML = '';
  q.scene.forEach(function (line) {
    const p = document.createElement('p');
    p.textContent = line;
    el.scene.appendChild(p);
  });
  el.scene.hidden = q.scene.length === 0;
  el.ask.textContent = q.ask;

  // 選択肢
  el.options.innerHTML = '';
  q.options.forEach(function (text, idx) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'option';
    btn.style.setProperty('--i', String(idx));
    if (state.answers[i] === idx) btn.classList.add('is-current');

    const dot = document.createElement('span');
    dot.className = 'option__dot';
    const label = document.createElement('span');
    label.className = 'option__label';
    label.textContent = text;

    btn.appendChild(dot);
    btn.appendChild(label);
    btn.addEventListener('click', function () { pick(idx, btn); });
    el.options.appendChild(btn);
  });

  if (animate) {
    el.qwrap.classList.remove('is-entering');
    void el.qwrap.offsetWidth;
    el.qwrap.classList.add('is-entering');
  }

  // 長い設問を下までスクロールして答えた後も、次の設問は先頭から始める
  window.scrollTo({ top: 0, behavior: 'auto' });
}

function pick(optionIndex, btn) {
  if (locked) return;
  locked = true;

  state.answers[state.index] = optionIndex;
  saveState();

  Array.prototype.forEach.call(el.options.children, function (child) {
    child.classList.remove('is-current', 'is-picked');
  });
  btn.classList.add('is-picked');

  setTimeout(function () {
    locked = false;
    goNext();
  }, AUTO_ADVANCE_MS);
}

function goNext() {
  if (state.index < QUESTIONS.length - 1) {
    state.index += 1;
    saveState();
    swapQuestion();
  } else {
    openFree();
  }
}

function goPrev() {
  if (state.index > 0) {
    state.index -= 1;
    saveState();
    swapQuestion();
  } else {
    show('start');
    refreshStart();
  }
}

function swapQuestion() {
  el.qwrap.classList.add('is-swapping');
  setTimeout(function () {
    el.qwrap.classList.remove('is-swapping');
    renderQuestion(true);
  }, 150);
}

function openQuestion(index) {
  state.index = clamp(index, 0, QUESTIONS.length - 1);
  saveState();
  show('quiz');
  renderQuestion(true);
}

/* =========================================================
   最後の任意質問
   ========================================================= */
function openFree() {
  el.freeLead.textContent = OPTIONAL_QUESTION.lead;
  el.freeAsk.textContent = OPTIONAL_QUESTION.ask;
  el.freeNote.textContent = OPTIONAL_QUESTION.note;
  el.freetext.placeholder = OPTIONAL_QUESTION.placeholder;
  el.freetext.value = state.free;
  show('free');
}

function finish(keepFree) {
  state.free = keepFree ? el.freetext.value.trim() : '';
  state.completed = true;
  saveState();
  el.preview.textContent = buildText();
  show('done');
}

/* =========================================================
   出力（コピー用テキスト / JSON / TXT）
   ========================================================= */
function answerTextOf(i) {
  const a = state.answers[i];
  return a === null ? '（未回答）' : QUESTIONS[i].options[a];
}

function buildText() {
  const blocks = QUESTIONS.map(function (q, i) {
    return '【' + q.id + ' ' + questionLabel(q) + '】\n' + answerTextOf(i);
  });
  blocks.push('【任意】\n' + (state.free ? state.free : '（未記入）'));
  return blocks.join('\n\n') + '\n';
}

function buildJson() {
  return JSON.stringify({
    version: SCHEMA_VERSION,
    answeredAt: state.updatedAt || new Date().toISOString(),
    answers: QUESTIONS.map(function (q, i) {
      return {
        id: q.id,
        question: questionLabel(q),
        options: q.options,
        selectedIndex: state.answers[i],
        selected: state.answers[i] === null ? null : q.options[state.answers[i]]
      };
    }),
    optional: {
      question: OPTIONAL_QUESTION.ask,
      answer: state.free || null
    }
  }, null, 2);
}

function timestampForFile() {
  const d = new Date();
  const p = function (n) { return String(n).padStart(2, '0'); };
  return d.getFullYear() + p(d.getMonth() + 1) + p(d.getDate()) + '-' + p(d.getHours()) + p(d.getMinutes());
}

function copyToClipboard(text, message) {
  const done = function () { toast(message); };
  const fallback = function () {
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.setAttribute('readonly', '');
    ta.style.position = 'fixed';
    ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.select();
    ta.setSelectionRange(0, ta.value.length);
    let ok = false;
    try { ok = document.execCommand('copy'); } catch (e) { ok = false; }
    document.body.removeChild(ta);
    toast(ok ? message : 'コピーできませんでした。下の内容を長押しで選択してね。');
  };

  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(text).then(done).catch(fallback);
  } else {
    fallback();
  }
}

function saveTxtViaLink(text, filename) {
  const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
  toast('TXTを保存しました');
}

function saveTxt() {
  const text = buildText();
  const filename = 'answers-' + timestampForFile() + '.txt';

  // ダウンロードが直接できない環境（埋め込み表示など）では、
  // 用意されている保存APIがあればそちらを使う
  if (window.claude && typeof window.claude.use === 'function') {
    window.claude.use('downloads').then(function (downloads) {
      if (!downloads) { saveTxtViaLink(text, filename); return; }
      downloads.save({ filename: filename, data: text }).then(function () {
        toast('TXTを保存しました');
      }).catch(function (err) {
        toast(err && err.code === 'declined' ? '保存をやめました' : 'TXTを保存できませんでした');
      });
    }).catch(function () { saveTxtViaLink(text, filename); });
    return;
  }

  saveTxtViaLink(text, filename);
}

let toastTimer = null;
function toast(message) {
  el.toast.textContent = message;
  el.toast.classList.add('is-visible');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(function () {
    el.toast.classList.remove('is-visible');
  }, 2200);
}

/* =========================================================
   トップ画面（続きから / やり直す）
   ========================================================= */
function refreshStart() {
  const saved = answeredCount() > 0 || state.free || state.completed;
  el.resumeBox.hidden = !saved;
  if (!saved) return;

  if (state.completed) {
    el.resumeText.textContent = '前回の回答が残っています。';
  } else {
    el.resumeText.textContent = '前回の続きがあります（' + answeredCount() + ' / ' + QUESTIONS.length + ' 問まで回答済み）。';
  }
}

function restart() {
  state = emptyState();
  clearState();
  el.freetext.value = '';
  refreshStart();
  show('start');
  toast('最初からになりました');
}

function resume() {
  if (state.completed) {
    el.preview.textContent = buildText();
    show('done');
    return;
  }
  // 未回答の最初の設問から再開する
  const next = state.answers.findIndex(function (a) { return a === null; });
  openQuestion(next === -1 ? QUESTIONS.length - 1 : next);
}

/* =========================================================
   イベント
   ========================================================= */
document.getElementById('btn-start').addEventListener('click', function () {
  if (answeredCount() > 0 || state.free || state.completed) {
    state = emptyState();
    clearState();
    el.freetext.value = '';
  }
  openQuestion(0);
});

document.getElementById('btn-resume').addEventListener('click', resume);
document.getElementById('btn-restart-start').addEventListener('click', restart);
document.getElementById('btn-restart-done').addEventListener('click', restart);

el.back.addEventListener('click', goPrev);
document.getElementById('btn-back-free').addEventListener('click', function () {
  state.free = el.freetext.value.trim();
  saveState();
  openQuestion(QUESTIONS.length - 1);
});

document.getElementById('btn-free-done').addEventListener('click', function () { finish(true); });
document.getElementById('btn-skip').addEventListener('click', function () { finish(false); });

el.freetext.addEventListener('input', function () {
  state.free = el.freetext.value;
  saveState();
});

document.getElementById('btn-copy').addEventListener('click', function () {
  copyToClipboard(buildText(), '回答をコピーしました');
});
document.getElementById('btn-copy-json').addEventListener('click', function () {
  copyToClipboard(buildJson(), 'JSONをコピーしました');
});
document.getElementById('btn-save-txt').addEventListener('click', saveTxt);
document.getElementById('btn-review').addEventListener('click', function () {
  openQuestion(QUESTIONS.length - 1);
});

/* =========================================================
   起動
   ========================================================= */
(function init() {
  const saved = loadState();
  if (saved) state = saved;
  el.freetext.value = state.free || '';
  refreshStart();
  show('start');
})();
