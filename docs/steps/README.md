# 実装ステップ

半日おでかけコース提案アプリを Step 0 から順に組み立てるためのガイド。
要件定義は `docs/requirement.md` を参照。

## MVP の方針（要件書からの変更点）

要件書 §3 では LLM がコースを組み立てる設計だが、MVP では以下に単純化する。

- **コースは事前に手で作って `courses.json` に持つ**（LLM に組み立てさせない）
- **LLM の役割はコース名と一言説明の生成のみ**（Step 4 で導入）
- API 呼び出しは1回だけ。失敗時は固定文にフォールバック

理由:
- LLM に組み立てさせると JSON パース失敗のリカバリが重く、初心者の1.5ヶ月では厳しい
- デモの主張（調べなくていい・時間が埋まる）はプリセットでも成立する
- API コストと設計負荷を最小化できる

## LLM に相談するときのコツ

- **`docs/requirement.md` + 該当ステップのファイル** を両方コピペして渡すと精度が上がる
- 「このステップのゴールを達成するコードを書いて」と明確に依頼する
- エラーが出たら、エラーメッセージと該当コードをそのまま貼る

## ステップ一覧

| # | ファイル | 週の目安 | ゴール |
|---|---|---|---|
| 0 | [00_setup.md](00_setup.md) | 済 | Flask が起動して "やったー" が表示される |
| 1 | [01_courses_data.md](01_courses_data.md) | 1週目 | `courses.json` を手で5件作り、Python で読み込める |
| 2 | [02_flask_display.md](02_flask_display.md) | 2週目 | `/` フォーム → `/suggest` で1件表示（フィルタなし） |
| 3 | [03_filter_and_weather.md](03_filter_and_weather.md) | 3週目 | 条件でフィルタ、天気切替で結果が変わる |
| 4 | [04_llm_naming.md](04_llm_naming.md) | 4週目 | Anthropic API でコース名と一言を生成、フォールバック実装 |
| 5 | [05_styling.md](05_styling.md) | 5週目 | CSS で見た目を整える |
| 6 | [06_demo_polish.md](06_demo_polish.md) | 6週目 | ローディング、別の案ボタン、リハーサル |

## ディレクトリ構成

MVP 完成時点で以下のような形になる想定。**Flask のシンプル構成に従ってフラット**。

```
geek_kazuki/
├── app.py               # 全ルート + Flask 初期化
├── courses.json         # 事前に作ったコース10〜20件
├── prompt.py            # Step 4 で追加（LLM プロンプト組み立て）
├── .env.example         # 環境変数テンプレ（Step 4 で追加）
├── .env                 # ローカル用（gitignore、Step 4 で追加）
├── .gitignore
├── pyproject.toml
├── uv.lock
├── README.md
│
├── templates/           # Step 2 以降で受講生が作る
│   ├── base.html        # 共通レイアウト（推奨）
│   ├── index.html       # 入力フォーム
│   └── result.html      # コース表示
│
├── static/              # Step 5 で作る
│   └── style.css
│
└── docs/                # 要件定義・実装ステップ
    ├── requirement.md
    └── steps/
```

### 迷いそうな場所メモ

- `templates/` は Flask の慣例で必須の場所名。`render_template("index.html")` はここを見に行く
- `static/` も慣例。`url_for("static", filename="style.css")` で参照

## 完成後の動作確認シナリオ

以下が通れば MVP 完成:

1. `/` にアクセス → 自由文入力欄・時間・天気（晴/雨）のフォームが出る
2. 「疲れてる、あんまり歩きたくない」+ 半日 + 晴 で送信 → コース1件が表示される
3. コース名・出発/帰宅時刻・スポット2〜3件・費用・条件バッジが見える
4. 戻って天気を「雨」に切り替えて送信 → 屋内だけのコースに変わる
5. 「別の案」ボタンで違うコースが出る
