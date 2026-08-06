# Step 4. LLM でコース名と一言を生成する

## ゴール
- Anthropic Claude API を呼び出して、表示するコースの **名前** と **一言説明** をその場で生成する
- スポットの選定・順番・時間はプリセットのまま（LLM に組み立てさせない）
- API 失敗時は `courses.json` に元から書いてある `name` / `description` を使う（フォールバック）
- API キーは `.env` に置き、リポジトリに含めない

## 触るファイル
- `.env`（新規、gitignore）
- `.env.example`（新規、コミットする）
- `.gitignore`（新規 or 更新）
- `pyproject.toml`（`anthropic`, `python-dotenv` を追加）
- `prompt.py`（新規）
- `app.py`（`/suggest` の中で `prompt.py` を呼ぶ）

## 前提コード

このステップを始める時点の `app.py`（Step 3 完了時の状態）:

```python
import json
from flask import Flask, render_template, request

app = Flask(__name__)

def load_courses():
    with open("courses.json", encoding="utf-8") as f:
        return json.load(f)

LOW_WORDS = ["疲れ", "だるい", "歩きたくない", "ゆっくり", "のんびり"]
HIGH_WORDS = ["元気", "がっつり", "動きたい", "たくさん"]

def guess_energy(free_text):
    text = free_text.lower()
    if any(w in text for w in LOW_WORDS):
        return "low"
    if any(w in text for w in HIGH_WORDS):
        return "high"
    return "mid"

def pick_course(courses, weather, duration, energy):
    candidates = courses
    if weather == "rainy":
        candidates = [c for c in candidates if c["indoor_only"]]
    if duration == "short":
        candidates = [c for c in candidates if c["total_duration_min"] <= 150]
    if not candidates:
        return courses[0]
    preferred = [c for c in candidates if c["energy_level"] == energy]
    return preferred[0] if preferred else candidates[0]

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/suggest", methods=["POST"])
def suggest():
    free_text = request.form.get("free_text", "")
    duration = request.form.get("duration", "half")
    weather = request.form.get("weather", "sunny")

    courses = load_courses()
    energy = guess_energy(free_text)
    course = pick_course(courses, weather, duration, energy)

    return render_template("result.html", course=course, weather=weather, matched_energy=energy)
```

## 事前準備

### 1. Anthropic API キーを取る

1. https://console.anthropic.com/ にアクセスしてサインアップ
2. 「API Keys」から新規キーを作成（`sk-ant-...` で始まる文字列）
3. 初回登録で無料クレジット（$5 相当）が付く。**MVP の開発では十分足りる**
4. Haiku モデル（`claude-haiku-4-5`）を使えば1回の呼び出しは $0.001 未満

### 2. 依存パッケージを追加

```bash
uv add anthropic python-dotenv
```

- `anthropic`: 公式の Claude SDK
- `python-dotenv`: `.env` ファイルから環境変数を読み込む

### 3. .env と .gitignore を作る

**`.env`**（絶対に git に含めない）:

```
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxx
```

**`.env.example`**（コミットする、キーは書かない）:

```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

**`.gitignore`**（既存に追記 or 新規）:

```
.env
__pycache__/
*.pyc
.venv/
```

すでにコミットしてしまった場合は `git rm --cached .env` で追跡から外す。

## LLM の役割（再確認）

**やらせること**: コースの表示用テキストの生成
- 新しい `name`（例: 「本と珈琲でだらだら池袋」→「雨の日、本を抱えて過ごす午後」）
- 新しい `description`（1〜2文）
- 「今日これを選んだ理由」の一言

**やらせないこと**: スポットの選定・順番・時間配分。これらは `courses.json` のまま使う。

この線引きが本作品の設計の主張なのでプレゼンで説明できるようにする。

## 実装

### prompt.py（新規）

```python
import json
import os
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
client = Anthropic()  # 環境変数 ANTHROPIC_API_KEY を自動で読む

SYSTEM_PROMPT = """あなたは半日おでかけコースを紹介するコピーライターです。
入力として渡されるコースの内容を元に、以下の JSON のみを返してください。
前置き・説明・コードフェンスは一切つけない。

{
  "name": "コース名(20文字以内)",
  "description": "一言説明(40文字以内、体言止めか常体)"
}
"""

def generate_naming(course: dict, free_text: str, weather: str) -> dict:
    """
    LLM で name と description を生成する。失敗したら None を返す。
    """
    user_content = f"""ユーザーの気分: {free_text or "特になし"}
天気: {"雨" if weather == "rainy" else "晴れ"}
エリア: {course["area"]}
スポット: {", ".join(s["name"] for s in course["spots"])}
所要時間: {course["total_duration_min"]}分
"""

    try:
        resp = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=200,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
        )
        text = resp.content[0].text.strip()
        data = json.loads(text)
        # 最低限の検証
        if "name" in data and "description" in data:
            return data
        print(f"[warn] LLM 応答に必須キーがない: {data}")
        return None
    except json.JSONDecodeError as e:
        print(f"[warn] LLM 応答が JSON でない: {e}\n生応答: {text!r}")
        return None
    except Exception as e:
        print(f"[warn] LLM 呼び出し失敗: {e}")
        return None
```

### app.py（`/suggest` に組み込む）

```python
from prompt import generate_naming

# ... 既存の import と関数はそのまま ...

@app.route("/suggest", methods=["POST"])
def suggest():
    free_text = request.form.get("free_text", "")
    duration = request.form.get("duration", "half")
    weather = request.form.get("weather", "sunny")

    courses = load_courses()
    energy = guess_energy(free_text)
    course = pick_course(courses, weather, duration, energy)

    # LLM で名前と説明を上書き。失敗したらプリセットを使う。
    ai_text = generate_naming(course, free_text, weather)
    if ai_text:
        course = dict(course)  # 元の courses.json を汚さないためコピー
        course["name"] = ai_text["name"]
        course["description"] = ai_text["description"]
        used_ai = True
    else:
        used_ai = False

    return render_template(
        "result.html",
        course=course,
        weather=weather,
        matched_energy=energy,
        used_ai=used_ai,
    )
```

### templates/result.html（AI 使用バッジを追加）

```html
{% if used_ai %}
  <p><small>コース名は AI が今日の気分に合わせて生成しました</small></p>
{% endif %}
```

## 動作確認

```bash
uv run flask --app app run --debug
```

1. フォームに「疲れてる、雨がだるい」等と入れて送信
2. コース名が `courses.json` に書いた元の名前と違うテキストに変わっている
3. **わざと `.env` を空にして再送信** → コンソールに `[warn]` が出て、`courses.json` の元の名前が表示される（フォールバック確認）

## プロンプト設計のコツ（要件書 §6.1 を実践する）

### 「JSON のみ」を強調する
Claude はデフォルトで説明文をつけたがる。プロンプトで明示的に禁止する。

- ○「JSON のみを出力してください。前置き・説明・コードフェンスを一切つけない」
- ×「JSON で返してください」（説明文が付いてくる）

### 期待する形式のサンプルをプロンプトに含める
上のコードでは `SYSTEM_PROMPT` にサンプル JSON を書いてある。これがないと Claude はキー名を勝手に変えることがある。

### max_tokens を小さくする
今回は名前と一言だけなので `max_tokens=200` で十分。大きくすると遅くなるしコストも増える。

## つまずきポイント

### `AuthenticationError` / 401
- `.env` の `ANTHROPIC_API_KEY=` の後ろが正しいキーか
- `.env` がプロジェクトルート（`app.py` と同じ場所）にあるか
- `load_dotenv()` を `Anthropic()` の前に呼んでいるか

### `.env` を git に push してしまった
1. Anthropic Console でそのキーを **即座に revoke**（漏れたキーは廃棄）
2. 新しいキーを発行して `.env` に書く
3. `.gitignore` に `.env` を追加してから `git rm --cached .env` → commit

### JSON パースが毎回失敗する
- `SYSTEM_PROMPT` で「JSON のみ」を強調
- コンソールに出る生応答をよく見る。コードフェンス（```json ... ```）が付いてる場合はプロンプトを強化
- それでも直らなければ、生応答から `{ ... }` の部分だけ正規表現で抜き出す簡易対策も可

### 応答が遅い
Haiku で 1〜3 秒程度が普通。5秒以上かかる場合はモデルを間違えてないか確認（`claude-haiku-4-5` を指定）。

### API コストが気になる
Haiku は 1M input tokens で $1、1M output tokens で $5。1回の呼び出しは 200〜500 tokens 程度なので $0.001 以下。開発中1000回叩いても $1 かからない。

## 完了チェック
- [ ] `.env` が gitignore されていて、`git status` に出てこない
- [ ] `/suggest` を叩くとコース名がプリセットと違う文字列に変わる
- [ ] `.env` を空にすると `[warn]` が出て、プリセットの名前が使われる
- [ ] コンソールに毎回 `[warn]` が出ていない（= JSON パースが安定して通っている）
