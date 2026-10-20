# Company Research Assistant

企業名を入力すると、gBizINFO・EDINETなどの公開情報を取得し、
企業基本情報・有価証券報告書・財務情報をまとめて取得する
企業リサーチアシスタントです。

現在はバックエンドのデータ取得・Databricksへの永続化・
企業リサーチAPIまで実装しています。

今後はOpenAI Agents SDKを利用し、
取得した企業情報をもとにAIがリサーチ結果を整理・分析する機能を追加予定です。

---

## Current Features

### Company Information

gBizINFO APIから企業情報を取得します。

- 企業名検索
- 法人番号
- 所在地
- 代表者
- 資本金
- 従業員数
- 事業概要
- 設立情報
- 業種
- 企業URL

企業名検索では会社種別を正規化し、
完全一致・前方一致などを考慮して検索結果を並び替えます。

---

### EDINET

EDINET APIから提出書類情報を取得します。

- 法人番号からEDINETコードを取得
- 有価証券報告書を検索
- EDINET CSVの取得
- CSVファイル一覧取得
- CSVプレビュー
- CSV内検索
- 財務情報抽出

現在取得している主な財務項目：

- 売上高
- 営業利益
- 税引前利益
- 親会社株主に帰属する利益
- 総資産
- 営業キャッシュフロー

IFRS・日本基準の両方を考慮して要素IDを検索しています。

---

## Databricks

EDINETの提出書類一覧はDatabricksに永続化します。

使用テーブル：

```text
workspace.default.edinet_documents
workspace.default.edinet_sync_history
```

### edinet_documents

EDINETの提出書類メタデータを保存します。

主な項目：

- doc_id
- edinet_code
- sec_code
- corporate_number
- filer_name
- doc_type_code
- period_start
- period_end
- submitted_at
- description
- xbrl_available
- pdf_available
- csv_available
- fetched_at

### edinet_sync_history

EDINET APIを取得済みの日付を管理します。

0件だった日も同期済みとして記録することで、
同じ日付に対して不要なAPIアクセスを繰り返さないようにしています。

## EDINET Sync

### Range Sync

指定した期間のEDINET書類一覧をDatabricksへ保存します。

```
POST /databricks/edinet-documents/sync-range


例：
start_date = 2026-06-08
end_date   = 2026-06-10
force      = false
```

同期済みの日付は自動的にskipします。

force=true を指定すると、
同期済みの日付でも再取得します。

## Latest Sync

Databricksの最新同期日を確認し、
その翌日から自動的に同期します。

```
POST /databricks/edinet-documents/sync-latest
```

現在は安全のため、
1回の実行につき最大7日分を同期します。

例：
latest sync date
2026-07-01

↓

next sync

2026-07-02
〜
2026-07-08

まだ同期対象の日付が残っている場合は、

```JSON
{
  "has_more": true,
  "next_start_date": "2026-07-09"
}
```

のように次の開始日を返します。

## Company Research

企業名から企業情報・最新有価証券報告書・財務情報をまとめて取得します。

```
GET /research/company
```

例：
name = 任天堂

処理の流れ：
Company Name
↓
gBizINFO
↓
Corporate Number
↓
EDINET Code
↓
Databricks
↓
Latest Annual Report
↓
EDINET CSV
↓
Financial Summary

## Architecture

```
src/app/
├── clients/
│   ├── databricks.py
│   ├── edinet.py
│   └── gbizinfo.py
│
├── models/
│   ├── company.py
│   ├── edinet.py
│   ├── edinet_sync.py
│   ├── financial.py
│   ├── gbizinfo.py
│   └── research.py
│
├── repositories/
│   ├── databricks_edinet_document.py
│   └── edinet_document_repository.py
│
├── services/
│   ├── company_research.py
│   └── edinet_sync.py
│
├── main.py
└── settings.py


基本的な責務：
main.py
    API / HTTP

services/
    アプリケーションの処理フロー

clients/
    外部API・外部サービスとの通信

repositories/
    データの保存・検索

models/
    Pydanticによるデータモデル・型定義

```

## Type Safety

外部APIのレスポンスを生の dict や Any のまま
アプリケーション内部へ渡さない方針にしています。

```
External API
    ↓
Pydantic Validation
    ↓
Typed Model
    ↓
Service
    ↓
Repository
```

EDINET・gBizINFOともに、
APIレスポンスをPydanticモデルへ変換してから利用します。

現在のコードでは原則として、

```
Any
cast()
response.json()
```

に依存せず、型付きモデルを利用しています。

## Development

### Requirements

- Python 3.12
- uv
- Databricks
- EDINET API Key
- gBizINFO API Key

### Install

uv sync

## Environment Variables

```
.env
OPENAI_API_KEY=
EDINET_API_KEY=
GBIZINFO_API_KEY=

DATABRICKS_SERVER_HOSTNAME=
DATABRICKS_HTTP_PATH=
DATABRICKS_TOKEN=
DATABRICKS_CATALOG=workspace
DATABRICKS_SCHEMA=default
```

.env はGit管理しません。

## Start API

```
uv run uvicorn app.main:app --reload --app-dir src

Swagger UI:
http://127.0.0.1:8000/docs

```

## Code Quality

Ruffとmypyを使用しています。

### Format

```
make fmt
```

### Lint

```
make lint
```

### Type Check

```
make typecheck
```

### All Checks

```
make check
```

### Type Audit

```
make type-audit
```

外部API由来の Any、cast()、生のdict、
response.json() などが残っていないか確認します。

## Current Status

実装済み：

- gBizINFO企業検索
- gBizINFO企業詳細取得
- EDINETコード取得
- EDINET提出書類取得
- 有価証券報告書検索
- EDINET CSV取得
- 財務情報抽出
- Databricks接続
- Deltaテーブルへの永続化
- 日付範囲同期
- 同期履歴管理
- 最新日からの継続同期
- 企業リサーチAPI
- Pydanticによる外部APIレスポンス検証
- Ruff / mypyによるコードチェック
