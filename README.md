# Oura Daily Log

Oura Ring の睡眠・アクティビティ・レディネスデータを毎朝自動取得し、Obsidian Vault 内の
`Health/oura-log.md` に1行ずつ追記する GitHub Actions ワークフローです。

- 取得元: Oura API v2 (`daily_sleep`, `daily_activity`, `daily_readiness`)
- 対象日: 実行時点(JST 07:00)から見て前日分
- 出力: `Health/oura-log.md` の Markdown テーブル（日付 / 睡眠スコア / 総睡眠時間 / レディネススコア / 活動スコア / 歩数）
- 同じ日付の行が既にある場合は追記をスキップします（冪等）
- ファイルやヘッダーが無い場合は自動生成します

## セットアップ手順

### 1. Oura Personal Access Token の発行

1. https://cloud.ouraring.com/personal-access-tokens にアクセスし、Oura アカウントでログイン
2. "Create New Personal Access Token" をクリックしてトークンを発行
3. 発行されたトークンをコピー（再表示できないので控えておく）

### 2. GitHub Secrets への登録

1. このリポジトリの **Settings → Secrets and variables → Actions** を開く
2. **New repository secret** をクリック
3. Name: `OURA_TOKEN`、Secret: 手順1で発行したトークンを入力して保存

### 3. ワークフローの動作確認

- `.github/workflows/oura.yml` は毎日 UTC 22:00（JST 7:00）に自動実行されます
- **Actions** タブから `Oura Daily Log` ワークフローを選択し、`Run workflow` で手動実行も可能です
- 実行後、取得したデータが自動で commit / push され、`Health/oura-log.md` が更新されます

### 4. Obsidian Git で Vault に同期する

このリポジトリを Obsidian Vault のルート（または Vault 内のサブフォルダ）として管理している場合、
[Obsidian Git](https://github.com/denolehov/obsidian-git) プラグインを使うと、GitHub 上の更新を
Obsidian アプリ側にも自動で反映できます。

1. Obsidian で Community Plugins から **Obsidian Git** をインストールし、有効化する
2. プラグイン設定でこのリポジトリを Vault のリモートとして設定する（既に `git init` 済みのフォルダを
   Vault として開くか、Vault フォルダ内でこのリポジトリを clone する）
3. 設定内の **Auto Pull** / **Pull on startup** や **Vault backup interval** を有効にしておくと、
   GitHub Actions が追記した内容が自動的に手元の Obsidian にも反映されます
4. 手元での編集を GitHub にも反映したい場合は、**Auto Backup** (commit + push) の間隔も併せて設定してください

これで、GitHub Actions が毎朝サーバー側で `Health/oura-log.md` を更新 → Obsidian Git がその変更を
Pull してくる、という流れで日々の健康データが自動的に Vault に蓄積されます。

## ローカルでの実行

```bash
pip install -r requirements.txt
export OURA_TOKEN=xxxxxxxx
python scripts/oura_daily_log.py
```
