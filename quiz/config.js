/**
 * 回答の保存先の設定。ここだけ書き換えれば送信先を変えられます。
 *
 * mode:
 *   'off'         … どこにも送信しない。回答は端末の中（localStorage）だけに残る
 *   'apps-script' … Google Apps Script のWebアプリとして公開する場合。
 *                   スプレッドシートへ直接保存する（送信先URLの設定は不要）
 *   'netlify'     … Netlify Forms に保存する。Netlifyで公開している場合
 *   'endpoint'    … 任意のURLへJSONで送信する
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
