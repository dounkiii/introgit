/**
 * 回答の保存先の設定。ここだけ書き換えれば送信先を変えられます。
 *
 * mode:
 *   'off'      … どこにも送信しない。回答は端末の中（localStorage）だけに残る
 *   'netlify'  … Netlify Forms に保存する。Netlifyで公開している場合はこれだけでOK
 *   'endpoint' … 任意のURLへ送信する。Google Apps Script などを使う場合
 *
 * endpoint:  mode が 'endpoint' のときの送信先URL
 * formName:  mode が 'netlify' のときのフォーム名（index.html の <form name="..."> と揃える）
 *
 * mode を 'off' 以外にすると、トップ画面の注意書きも自動で
 * 「送信されます」という表現に切り替わります。
 */
const SUBMIT_CONFIG = {
  mode: 'off',
  endpoint: '',
  formName: 'quiz-answers'
};
