# Instagram 自動投稿パイプライン

`queue/` に写真を置いてpushしておくだけで、毎週 **火・木・土 18:00 (JST)** に
1枚ずつ自動でInstagramに投稿されます。キャプションはClaudeが写真を見て生成します。

コストの目安（週3投稿ペース）:
- GitHub Actions: 無料枠内（公開リポジトリなら無制限、非公開でも月2,000分の無料枠で十分足りる）
- Instagram Graph API: 無料
- Claude API: 1回あたり数円〜十数円 → 月100〜200円程度

---

## 1. リポジトリを作る（重要: 公開リポジトリにする）

Instagram Graph API は投稿する画像を「公開URL」として取得しに来るため、
このパイプラインでは `raw.githubusercontent.com` の生ファイルURLをそのまま使います。
非公開リポジトリだとこのURLに認証がかかり、Instagram側から画像を取得できません。

→ このリポジトリ自体は **Public** で作成してください（GitHub Secretsはpublicリポジトリでも
外部から読めないので安全です）。写真は投稿する少し前から一時的に公開状態になりますが、
そもそも数分後にInstagramへ公開する写真なので実質的な影響はありません。

## 2. Instagramをビジネス/クリエイターアカウントにする

1. Instagramアプリ → 設定 → アカウントの種類を「プロアカウント」に切り替え（無料）
2. Facebookページを作成し、Instagramアカウントと連携

## 3. Meta for Developersでアプリを作り、長期アクセストークンを取得

1. https://developers.facebook.com/ でアプリを新規作成
2. 「Instagram Graph API」を追加
3. 短期トークン→長期トークン（60日）に交換する手順に従い、`IG_ACCESS_TOKEN` を発行
   - 60日で失効するため、期限前に再発行してSecretsを更新する運用が必要です
     （カレンダーにリマインドを入れておくのがおすすめ）
4. 連携したFacebookページからInstagramビジネスアカウントID（`IG_BUSINESS_ACCOUNT_ID`）を取得
   - `GET https://graph.facebook.com/v21.0/me/accounts` → ページID
   - `GET https://graph.facebook.com/v21.0/{page-id}?fields=instagram_business_account` → IG ID

## 4. GitHub Secretsを登録

リポジトリの Settings → Secrets and variables → Actions で以下を登録:

| Secret名 | 内容 |
|---|---|
| `ANTHROPIC_API_KEY` | Claude APIキー（console.anthropic.com で発行） |
| `IG_ACCESS_TOKEN` | 手順3で取得した長期アクセストークン |
| `IG_BUSINESS_ACCOUNT_ID` | 手順3で取得したInstagramビジネスアカウントID |

## 5. 写真を投稿する

`queue/` フォルダに写真（jpg/png）を1枚以上置いてpushするだけです。
ファイル名の昇順で1回につき1枚、自動的に選ばれて投稿されます。
投稿済みの写真は自動で `posted/` フォルダに移動されます。

手動でテストしたい場合は、GitHubの Actions タブから
「Instagram Auto Post」→「Run workflow」でいつでも手動実行できます。

## キャプションのスタイルを調整したい場合

`scripts/post_to_instagram.py` 内の `CAPTION_SYSTEM_PROMPT` を編集してください。
今は「事実ベースの描写＋ハッシュタグ8〜15個」というスタイルにしてあります。
