# Step 3. 条件でフィルタする（天気切替を効かせる）

## ゴール
- フォームの入力に応じて、`courses.json` から条件に合うコースを絞り込む
- 天気を「雨」にすると屋内コースだけになる
- 「疲れてる」系のキーワードが含まれると energy_level=low が優先される
- 該当が0件のときはフォールバックで最初の1件を返す（デモでコケないため）
- **「別の案」機能はまだ実装しない**（Step 6 でやる）

## 触るファイル
- `app.py`（`/suggest` の中身を書き換え）

## 前提コード

このステップを始める時点の `app.py`（Step 2 完了時の状態）:

```python
import json
from flask import Flask, render_template, request

app = Flask(__name__)

def load_courses():
    with open("courses.json", encoding="utf-8") as f:
        return json.load(f)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/suggest", methods=["POST"])
def suggest():
    free_text = request.form.get("free_text", "")
    duration = request.form.get("duration", "half")
    weather = request.form.get("weather", "sunny")

    courses = load_courses()
    course = courses[0]  # ← ここを条件フィルタに変える

    return render_template("result.html", course=course, weather=weather)
```

`courses.json` の各要素は Step 1 のスキーマ通り（`indoor_only` / `energy_level` / `total_duration_min` 等を持つ）。

## フィルタ設計

要件書 §4.1 の入力を元に、以下の順で絞り込む。

### ステップ1: 天気で切る（ハード制約）

雨なら `indoor_only == true` のコースのみ通す。晴れなら制約なし。

### ステップ2: 時間で切る（ハード制約）

`duration == "short"` なら `total_duration_min <= 150`（2.5時間まで）
`duration == "half"` なら制約なし（半日 = すべて許容）

### ステップ3: 自由文からタグを抽出（ソフト優先）

自由文に含まれるキーワードで energy_level を推定する。**LLM は使わない**。単純な文字列マッチで十分。

| キーワード（自由文に含まれれば） | 優先する energy_level |
|---|---|
| 疲れ / だるい / 歩きたくない / ゆっくり / のんびり | `low` |
| 元気 / がっつり / 動きたい / たくさん | `high` |
| （どれも該当しない） | `mid` を優先、なければ何でも |

ソフト制約は「合致するコースがあればそれを、なければ他のを返す」。ハードで0件になるのは避ける。

### ステップ4: フォールバック

ハード制約で0件になったら、`courses.json` の1件目を返す（要件書 §6.1 の思想）。
コンソールに warning を print しておくと、あとで「フォールバックが発動した」ことに気づける。

## 実装

### app.py（差し替え）

```python
import json
from flask import Flask, render_template, request

app = Flask(__name__)

def load_courses():
    with open("courses.json", encoding="utf-8") as f:
        return json.load(f)

# 自由文からエネルギーレベルを推定
LOW_WORDS = ["疲れ", "だるい", "歩きたくない", "ゆっくり", "のんびり"]
HIGH_WORDS = ["元気", "がっつり", "動きたい", "たくさん"]

def guess_energy(free_text: str) -> str:
    text = free_text.lower()
    if any(w in text for w in LOW_WORDS):
        return "low"
    if any(w in text for w in HIGH_WORDS):
        return "high"
    return "mid"

def pick_course(courses, weather: str, duration: str, energy: str):
    # ハード制約
    candidates = courses
    if weather == "rainy":
        candidates = [c for c in candidates if c["indoor_only"]]
    if duration == "short":
        candidates = [c for c in candidates if c["total_duration_min"] <= 150]

    if not candidates:
        print("[warn] ハード制約で0件。フォールバック発動")
        return courses[0]

    # ソフト制約: energy が一致するのを優先
    preferred = [c for c in candidates if c["energy_level"] == energy]
    if preferred:
        return preferred[0]
    return candidates[0]

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

    return render_template(
        "result.html",
        course=course,
        weather=weather,
        matched_energy=energy,
    )
```

### templates/result.html（バッジに反映）

すでに Step 2 で作った `result.html` の、天気表示部分を少し充実させる。

```html
<p>
  {% if course.indoor_only %}<span>全部屋内</span>{% endif %}
  {% if course.solo_friendly %}<span>1人向け</span>{% endif %}
  <span>天気: {{ "雨" if weather == "rainy" else "晴れ" }}</span>
  <span>疲労度マッチ: {{ matched_energy }}</span>
</p>
```

## 動作確認

Step 1 で作った5件が以下を満たしていれば、下の確認が通る。
- `indoor_only: true` が2件以上
- `energy_level` に `low` / `mid` / `high` が1件以上ずつ

### 確認シナリオ

1. 自由文「疲れてる」+ 半日 + 晴れ → energy=low のコースが出る
2. 同じ入力で天気を「雨」に変える → indoor_only=true かつ energy=low のコースに変わる
3. 自由文「元気にたくさん歩きたい」+ 半日 + 晴れ → energy=high のコースが出る
4. 天気「雨」+ 時間「2時間」+ 自由文「元気」 → 屋内かつ短時間で絞り、それでも該当なければフォールバック

## 設計上の注意

### なぜ LLM で自由文を解釈しないのか
MVP のスコープを狭めるため。単純なキーワードマッチで9割の入力はさばける。
デモで「AI が言葉を理解してます」と言いたくなるが、そこは Step 4 の名前生成でカバーする。

### なぜ0件フォールバックが必須か
要件書 §6.1 と同じ思想。**デモ中に「該当なし」と出た瞬間、価値が消える**。
プレゼンター（受講生）は「該当なし」を見た瞬間パニックになる。無理やり1件返す方が良い。

### なぜ energy はソフト制約か
ハードにすると0件が増える。天気と時間はデモの主張に直結するのでハード、energy は「あるとうれしい」なのでソフト。

## つまずきポイント

### `KeyError: 'indoor_only'`
`courses.json` のあるコースにキーが抜けてる。全件に必須項目が揃っているか確認。

### 天気を切り替えても結果が変わらない
- `courses.json` の `indoor_only` が全部 true になってないか？
- HTML の `<input name="weather" value="rainy">` の value と Python の `"rainy"` が一致してるか？

### `guess_energy` が常に mid を返す
- 自由文が英語だと日本語キーワードにマッチしない。デモは日本語で入れる想定
- `LOW_WORDS` のスペルミス確認

## 完了チェック
- [ ] 「疲れてる」+ 晴れ → energy=low のコースが出る
- [ ] 天気を雨に切り替えると屋内のみになる
- [ ] 時間「2時間」で `total_duration_min <= 150` のコースだけが候補になる
- [ ] 「元気」+ 短時間 + 雨 で該当なしになる場合、フォールバックで何か出る
- [ ] フォールバック時にコンソールに `[warn]` が出る
