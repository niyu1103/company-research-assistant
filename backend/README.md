# Company Research Assistant

企業名を入力すると、gBizINFO・EDINETなどの公開情報を取得し、  
企業基本情報・有価証券報告書・財務情報を横断して検索・分析する  
AI企業リサーチアシスタントです。

FastAPIを中心に、gBizINFO・EDINET・Databricks・OpenAI Agents SDKを組み合わせています。

現在は以下まで実装しています。

- 企業基本情報の取得
- EDINET有価証券報告書の取得
- 財務情報の抽出・比較
- Databricksへの永続化
- 過去年度有報の自動取得
- 有価証券報告書を対象としたRAG
- 財務質問のPlanner
- 企業分析
- 曖昧な期間表現の解決
- Conversation Stateを利用した確認・再質問フロー

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

## EDINET

EDINET APIから提出書類情報を取得します。

- 法人番号からEDINETコードを取得
- 有価証券報告書を検索
- EDINET CSVの取得
- CSVファイル一覧取得
- CSVプレビュー
- CSV内検索
- 財務情報抽出
- 過去年度の有価証券報告書取得

現在取得している主な財務項目：

- 売上高
- 営業利益
- 税引前利益
- 純利益
- 総資産
- 営業キャッシュフロー

IFRS・日本基準の両方を考慮して要素IDを検索しています。

古い有価証券報告書で利用される以下のようなContext IDにも対応しています。

```text
CurrentYearDuration_NonConsolidatedMember
Prior1YearDuration_NonConsolidatedMember
```

---

## Historical Financial Data

最新の有価証券報告書だけでは取得できない過去年度については、  
対象年度の有価証券報告書をEDINETから検索します。

Databricksに対象年度の書類が存在しない場合は、

```text
Requested Year
    ↓
Databricks検索
    ↓
対象年度なし
    ↓
最新有報の提出タイミングから提出日を推定
    ↓
EDINET検索
    ↓
対象年度の有報を取得
    ↓
Databricksへ同期
    ↓
財務データ取得
```

という流れで自動取得します。

これにより、例えば以下のような質問に対応できます。

```text
2020年と2023年の売上を比較して
```

---

## Databricks

EDINETの提出書類情報をDatabricksに永続化します。

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
- source_date
- description
- xbrl_available
- pdf_available
- csv_available
- fetched_at

### edinet_sync_history

EDINET APIを取得済みの日付を管理します。

0件だった日も同期済みとして記録することで、  
同じ日付に対して不要なAPIアクセスを繰り返さないようにしています。

---

## EDINET Sync

### Range Sync

指定した期間のEDINET書類一覧をDatabricksへ保存します。

```text
POST /databricks/edinet-documents/sync-range
```

例：

```text
start_date = 2026-06-08
end_date   = 2026-06-10
force      = false
```

同期済みの日付は自動的にskipします。

`force=true` を指定すると、同期済みの日付でも再取得します。

### Latest Sync

Databricksの最新同期日を確認し、その翌日から自動的に同期します。

```text
POST /databricks/edinet-documents/sync-latest
```

現在は安全のため、1回の実行につき最大7日分を同期します。

---

## Company Research

企業名から企業情報・最新有価証券報告書・財務情報をまとめて取得します。

```text
GET /research/company
```

処理の流れ：

```text
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
```

---

## Company QA

企業について自然言語で質問できます。

```text
POST /research/company/qa
```

質問内容は `CompanyQuestionRouterService` によって分類されます。

主なルート：

```text
company_facts
financial
document
analysis
```

それぞれ用途に応じたServiceへ処理を分岐します。

---

## Financial Question Planner

財務質問は `FinancialQuestionPlannerService` が構造化します。

例えば、

```text
過去5期で一番売上が高かったのは？
```

という質問から、

```text
metric = revenue
operation = max
years = 5
```

のようなPlanを生成します。

主な処理：

- 最新値
- 最大値
- 最小値
- 利用可能年度
- 特定年度比較
- 複数年度の業績確認

明示的な西暦については、LLMだけに依存せず正規表現でも抽出します。

---

## Historical Period Resolver

「コロナ禍」「リーマンショック」など、  
明示的な西暦ではない期間表現を財務分析で利用できる期間へ変換します。

例：

```text
コロナ禍
    ↓
2020年〜2023年
```

厳密な開始日・終了日が一意でなくても、  
年単位の代表期間として十分に妥当な場合は候補期間を返します。

ただし、その期間をAIだけで確定して分析するのではなく、  
必要に応じてユーザーへ確認します。

---

## Conversation State

曖昧な期間や追加確認が必要な質問では、  
`conversation_id` を利用して処理途中のStateをBackend側に保持します。

例：

```text
User
「コロナ禍で売上は上がりましたか？」

Assistant
「コロナ禍を2020年〜2023年として比較してよいですか？」

User
「はい」

Assistant
2020年と2023年の財務データを取得して比較
```

確認後は、Stateに保存していた

- 元の質問
- 企業名
- FinancialQuestionPlan
- Resolverが提案した期間

を復元し、途中から処理を再開します。

### Period Change

ユーザーは候補期間を変更できます。

```text
Assistant
「コロナ禍を2020年〜2023年として比較してよいですか？」

User
「期間を変更したい」

Assistant
「比較したい期間を2020年〜2022年のように入力してください。」

User
「2021年〜2023年で」
```

変更後の期間で元の財務質問を再実行します。

### Period Scope Validation

元の質問の意味と大きく異なる期間が指定された場合は、  
そのまま処理せず再確認します。

例：

```text
Original:
コロナ禍

Resolved Period:
2020年〜2023年

User Requested:
2000年〜2023年
```

この場合、

```text
指定された2000年〜2023年には、
コロナ禍として解釈した2020年〜2023年の範囲外が含まれています。
どの期間を使用しますか？
```

と確認し、

```text
- 2020年〜2023年で確認する
- 2000年〜2023年のまま確認する
- 別の期間を入力する
```

という選択肢を返します。

現在のConversation State Storeはインメモリ実装です。

そのため、アプリケーション再起動時にはStateが失われます。  
将来的にはRedisなどへの移行を想定しています。

---

## Document QA / RAG

有価証券報告書をDatabricksへ保存・インデックス化し、  
Vector Searchを利用したDocument QAを行います。

処理の流れ：

```text
Question
    ↓
Question Router
    ↓
Query Planning
    ↓
Document Retrieval
    ↓
Context Sufficiency Evaluation
    ↓
Document Answering
```

取得したContextだけでは回答に必要な情報が不足している場合は、  
推測で回答せず `insufficient_context=true` を返します。

---

## Company Analysis

財務データと有価証券報告書の検索結果を組み合わせ、  
複数情報を統合した企業分析を行います。

Document QAとは処理を分離し、

- 財務トレンド
- 有価証券報告書の検索結果
- 企業情報

を組み合わせて回答します。

---

## Architecture

```text
src/app/
├── clients/
│   ├── databricks.py
│   ├── edinet.py
│   └── gbizinfo.py
│
├── models/
│   ├── company.py
│   ├── conversation_state.py
│   ├── document_qa.py
│   ├── edinet.py
│   ├── financial.py
│   ├── financial_question.py
│   ├── historical_period.py
│   └── research.py
│
├── repositories/
│   ├── databricks_edinet_document.py
│   └── edinet_document_repository.py
│
├── services/
│   ├── company_analysis.py
│   ├── company_document_qa.py
│   ├── company_financial.py
│   ├── company_research.py
│   ├── conversation_state.py
│   ├── document_answering.py
│   ├── document_retrieval.py
│   ├── edinet_sync.py
│   ├── financial_question_planner.py
│   └── historical_period_resolver.py
│
├── main.py
└── settings.py
```

基本的な責務：

```text
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

---

## Type Safety

外部APIやLLMのレスポンスを、生の `dict` や `Any` のまま  
アプリケーション内部へ渡さない方針にしています。

```text
External API / Agent
    ↓
Pydantic Validation
    ↓
Typed Model
    ↓
Service
    ↓
Repository
```

原則として、

```text
Any
cast()
response.json()
```

への依存を避け、型付きモデルを利用します。

AgentのStructured Outputについても `model_validate()` を利用し、  
アプリケーション境界で型を検証します。

---

## Development

### Requirements

- Python 3.12
- uv
- Databricks
- OpenAI API Key
- EDINET API Key
- gBizINFO API Key

### Install

```bash
uv sync
```

---

## Environment Variables

```env
OPENAI_API_KEY=
EDINET_API_KEY=
GBIZINFO_API_KEY=

DATABRICKS_SERVER_HOSTNAME=
DATABRICKS_HTTP_PATH=
DATABRICKS_TOKEN=
DATABRICKS_CATALOG=workspace
DATABRICKS_SCHEMA=default
```

`.env` はGit管理しません。

---

## Start API

```bash
uv run uvicorn app.main:app --reload --app-dir src
```

Swagger UI：

```text
http://127.0.0.1:8000/docs
```

---

## Code Quality

Ruff・mypy・pytestを利用しています。

### Format

```bash
make fmt
```

### Lint

```bash
make lint
```

### Type Check

```bash
make typecheck
```

### Test

```bash
make test
```

### All Checks

```bash
make check
```

現在：

```text
77 passed
```

### Type Audit

```bash
make type-audit
```

外部API由来の `Any`、`cast()`、生のdict、  
`response.json()` などが残っていないか確認します。

---

## Current Status

実装済み：

- gBizINFO企業検索
- gBizINFO企業詳細取得
- EDINETコード取得
- EDINET提出書類取得
- 有価証券報告書検索
- EDINET CSV取得
- 財務情報抽出
- 過去年度有報の自動取得
- Databricks接続
- Deltaテーブルへの永続化
- 日付範囲同期
- 同期履歴管理
- 最新日からの継続同期
- 企業リサーチAPI
- Company QA API
- Financial Question Planner
- 特定年度財務比較
- Document QA / RAG
- Context Sufficiency Evaluation
- Company Analysis
- Historical Period Resolver
- Conversation State
- 期間確認・変更・再入力
- 元質問と矛盾する期間指定の再確認
- Pydanticによる外部API / Agent出力検証
- Ruff / mypy / pytestによるコードチェック

---
