# Step 6. デモ耐性を上げる

## ゴール
- LLM 呼び出し中に「ローディング表示」が出る（無反応で「壊れた」に見えない）
- 「別の案」ボタンで、同じ条件で違うコースを再表示できる（回数制限あり）
- デモで使う定番の入力パターンをリハーサルできる
- LLM 呼び出しをオフにする開発モードがある（オフライン確認用）

## 触るファイル
- `app.py`（`/suggest` にセッション or クエリで shown_ids を持たせる、`SKIP_LLM` フラグ追加）
- `templates/index.html`（フォーム送信時にローディング表示）
- `templates/result.html`（「別の案」ボタン追加）
- `static/style.css`（ローディング用スタイル）

## 前提コード

Step 5 完了時点の `app.py`:

```python
import json
from flask import Flask, render_template, request
from prompt import generate_naming

app = Flask(__name__)

def load_courses():
    with open("courses.json", encoding="utf-8") as f:
        return json.load(f)

LOW_WORDS = ["疲れ", "だるい", "歩きたくない", "ゆっくり", "のんびり"]
HIGH_WORDS = ["元気", "がっつり", "動きたい", "たくさん"]

def guess_energy(free_text):
    text = free_text.lower()
    if any(w in text for w in LOW_WORDS): return "low"
    if any(w in text for w in HIGH_WORDS): return "high"
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

    ai_text = generate_naming(course, free_text, weather)
    if ai_text:
        course = dict(course)
        course["name"] = ai_text["name"]
        course["description"] = ai_text["description"]
        used_ai = True
    else:
        used_ai = False

    return render_template("result.html", course=course, weather=weather,
                          matched_energy=energy, used_ai=used_ai)
```

## 1. 「別の案」ボタン

### 設計

- 表示中のコース ID を hidden で受け取り、除外して次を選ぶ
- 3回まで押せる（それを超えたら決定麻痺に戻るので要件書 §4.2 通り制限）
- 「別の案」で全部見尽くしたら、そこで打ち止め

### app.py（更新）

`pick_course` に「除外リスト」を渡せるようにする。

```python
def pick_course(courses, weather, duration, energy, excluded_ids=None):
    excluded_ids = excluded_ids or []
    candidates = [c for c in courses if c["id"] not in excluded_ids]

    if weather == "rainy":
        candidates = [c for c in candidates if c["indoor_only"]]
    if duration == "short":
        candidates = [c for c in candidates if c["total_duration_min"] <= 150]

    if not candidates:
        return None  # 全部除外されたら None を返す

    preferred = [c for c in candidates if c["energy_level"] == energy]
    return preferred[0] if preferred else candidates[0]

@app.route("/suggest", methods=["POST"])
def suggest():
    free_text = request.form.get("free_text", "")
    duration = request.form.get("duration", "half")
    weather = request.form.get("weather", "sunny")
    # 「別の案」で回ってきた除外リスト（カンマ区切り）
    excluded_raw = request.form.get("excluded", "")
    excluded_ids = [x for x in excluded_raw.split(",") if x]

    courses = load_courses()
    energy = guess_energy(free_text)
    course = pick_course(courses, weather, duration, energy, excluded_ids)

    # 全部見尽くした
    if course is None:
        return render_template("no_more.html")

    ai_text = generate_naming(course, free_text, weather)
    if ai_text:
        course = dict(course)
        course["name"] = ai_text["name"]
        course["description"] = ai_text["description"]
        used_ai = True
    else:
        used_ai = False

    # 次の「別の案」で使う除外リスト（今回のを追加）
    next_excluded = ",".join(excluded_ids + [course["id"]])
    # 残り回数(表示用)
    remaining = max(0, 3 - len(excluded_ids))

    return render_template(
        "result.html",
        course=course, weather=weather, matched_energy=energy,
        used_ai=used_ai,
        free_text=free_text, duration=duration,
        next_excluded=next_excluded, remaining=remaining,
    )
```

### templates/result.html（「別の案」ボタン追加）

`{% endblock %}` の前あたりに追加:

```html
{% if remaining > 0 %}
  <form action="/suggest" method="post" class="another">
    <input type="hidden" name="free_text" value="{{ free_text }}">
    <input type="hidden" name="duration" value="{{ duration }}">
    <input type="hidden" name="weather" value="{{ weather }}">
    <input type="hidden" name="excluded" value="{{ next_excluded }}">
    <button type="submit" class="button-secondary">
      別の案（あと{{ remaining }}回）
    </button>
  </form>
{% else %}
  <p class="another-limit">別の案はここまで。決めてください。</p>
{% endif %}
```

### templates/no_more.html（新規）

条件に合うコースを全部見尽くした時。

```html
{% extends "base.html" %}
{% block content %}
  <h1>候補を出し切りました</h1>
  <p>この条件で提案できるコースは以上です。</p>
  <p><a href="/">条件を変えて試す</a></p>
{% endblock %}
```

## 2. ローディング表示

### なぜ必要か
LLM 呼び出しは 1〜3 秒かかる。無反応だと「壊れた」と見える（要件書 §6.2）。

### 実装方針
サーバーサイドレンダリング（現在の構成）では、送信ボタンを押した瞬間にブラウザが「読み込み中」状態になる。**その状態でユーザーに何かフィードバックを出す** のが最小コストで済む。JavaScript は最小限。

### templates/index.html（更新）

`<form>` タグに id と、その下にローディング表示用の div を足す。

```html
<form action="/suggest" method="post" class="form" id="ask-form">
  <!-- ... 既存のフォーム内容 ... -->
</form>

<div id="loading" class="loading" hidden>
  <div class="spinner"></div>
  <p>AI があなたの半日を組み立てています…</p>
</div>

<script>
  document.getElementById("ask-form").addEventListener("submit", () => {
    document.getElementById("ask-form").hidden = true;
    document.getElementById("loading").hidden = false;
  });
</script>
```

### static/style.css（追記）

```css
.loading {
  text-align: center;
  padding: 60px 20px;
  color: var(--muted);
}

.spinner {
  width: 40px;
  height: 40px;
  margin: 0 auto 16px;
  border: 3px solid var(--line);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.button-secondary {
  padding: 10px 16px;
  background: transparent;
  color: var(--accent);
  border: 1px solid var(--accent);
  border-radius: 8px;
  font-size: 0.9rem;
  cursor: pointer;
  margin-top: 20px;
}

.another-limit {
  font-size: 0.85rem;
  color: var(--muted);
  margin-top: 20px;
  text-align: center;
}
```

## 3. LLM オフモード（開発用）

デモ会場のネットが不安な時、あるいは API キーが切れた時のために、LLM 呼び出しを止められるフラグを入れる。

### app.py（更新）

```python
import os
# ... 既存の import ...

SKIP_LLM = os.getenv("SKIP_LLM") == "1"

# suggest() の中の該当箇所を差し替え:
if SKIP_LLM:
    ai_text = None
    print("[info] SKIP_LLM=1: LLM 呼び出しをスキップ")
else:
    ai_text = generate_naming(course, free_text, weather)
```

### 使い方

```bash
# LLM を使わないモードで起動
SKIP_LLM=1 uv run flask --app app run --debug
```

デモ会場ではまず SKIP_LLM=1 で全機能を動かし、ネットが安定してるのを確認してから SKIP_LLM を外す、という運用ができる。

## 4. デモ台本（要件書 §8）

デモは以下の流れで通す。事前に何度もリハーサルすること。

| # | 動作 | 話すこと |
|---|---|---|
| 1 | 何もしない | 「休みの日、外出たいけど結局家にいたことないですか？」 |
| 2 | スマホを見せる | 「地図見て、インスタ見て、ルート調べて…がだるい」 |
| 3 | フォームに「疲れてる」入力 → 半日 → 晴れ → 送信 | 「気分を1文入れるだけ」 |
| 4 | 結果表示（ローディング → コース1件） | 「屋外含む、ゆっくり系のコースを組んでくれた」 |
| 5 | 戻る → 天気を「雨」に変更 → 送信 | 「天気変えるとどうなるか」 |
| 6 | 屋内のみのコースに変わる | 「屋内だけに組み替わりました」 |
| 7 | 「1人でも3時間半、ちゃんと埋まります」 | 締め |

**要件書 §8 の完成の定義とほぼ同じ**。3 と 6 で驚きが起きれば勝ち。

## 5. デモ前チェックリスト

- [ ] `SKIP_LLM=1` で起動して全画面が動くことを確認
- [ ] `SKIP_LLM` を外して LLM 呼び出しが 3 秒以内に返ることを確認
- [ ] `.env` に有効な API キーが入っている
- [ ] Anthropic Console でクレジット残高を確認（$0 じゃないこと）
- [ ] 「疲れてる」→ 天気切替 の動作が期待通り
- [ ] スマホ幅で崩れない
- [ ] ブラウザのタブを事前に開いておく（当日 URL を打つ余裕はない）
- [ ] Wi-Fi が不安定な会場では有線 LAN or テザリング準備

## つまずきポイント

### 「別の案」を押すと同じコースが出る
- `excluded_ids` が hidden で正しく渡っているか。DevTools で form の hidden 値を確認
- `pick_course` の `not in excluded_ids` の判定でタイポしてないか

### ローディングが一瞬しか出ない
それは正常。速い方が良い（要件書 §6.2）。「わざと長く見せない」

### `SKIP_LLM=1` にしても LLM が呼ばれる
- 環境変数の設定タイミング。`SKIP_LLM=1 uv run flask ...` のように **同じ行の先頭** に書く
- `.env` に `SKIP_LLM=1` を書いた場合、`load_dotenv()` が呼ばれる前に読む必要あり

## 完了チェック
- [ ] LLM 呼び出し中にスピナーが表示される
- [ ] 「別の案」ボタンで違うコースが出る
- [ ] 3回で打ち止めになる
- [ ] 全部見尽くしたら `no_more.html` が出る
- [ ] `SKIP_LLM=1` で LLM なしでも全機能動く
- [ ] 要件書 §8 のデモ台本を、詰まらずに3回連続で通せる
