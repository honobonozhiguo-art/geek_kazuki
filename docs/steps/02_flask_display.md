# Step 2. Flask でコースを1件表示する

## ゴール
- `/` にアクセスすると、自由文入力・時間・天気を選ぶフォームが出る
- フォームを送信すると `/suggest` で `courses.json` の1件目を表示する
- **フィルタはまだ実装しない**（次のステップでやる）
- 「まず画面に何か出す」を最速で達成する

## 触るファイル
- `app.py`（書き換え）
- `templates/index.html`（新規）
- `templates/result.html`（新規）

## 前提コード

このステップを始める時点の `courses.json` の構造（Step 1 で作ったもの）:

```json
[
  {
    "id": "cafe_book_ikebukuro",
    "name": "本と珈琲でだらだら池袋",
    "description": "歩き回らずゆっくり過ごす3時間半",
    "area": "池袋",
    "total_duration_min": 210,
    "total_cost_yen": 2500,
    "indoor_only": true,
    "solo_friendly": true,
    "energy_level": "low",
    "spots": [
      { "time": "13:00", "name": "梟書茶房", "stay_min": 90, "note": "..." },
      { "time": "14:45", "name": "ジュンク堂書店", "stay_min": 75, "note": "..." }
    ]
  }
]
```

このステップを始める時点の `app.py`（Step 0 の状態）:

```python
from flask import Flask
app = Flask(__name__)

@app.route("/")
def home():
    return "やったー"
```

## Flask の基礎（初めての人向け）

### ルート
`@app.route("/") def home(): ...` は「/ にアクセスされたら `home` を実行する」の意味。
POST を受けたい時は `@app.route("/suggest", methods=["POST"])` と書く。

### テンプレート
HTML を Python の文字列で書くと死ぬので、`templates/` フォルダに `.html` を置いて `render_template("index.html")` で読み込む。
Python の変数を渡したい時は `render_template("result.html", course=course)` のようにキーワード引数で渡し、HTML 側では `{{ course.name }}` のように書く。

### フォームからの値の受け取り
```python
from flask import request
free_text = request.form.get("free_text")  # <input name="free_text"> の値
```

## 実装

### app.py

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
    duration = request.form.get("duration", "half")   # "short" or "half"
    weather = request.form.get("weather", "sunny")    # "sunny" or "rainy"

    courses = load_courses()
    # MVP: とりあえず1件目を返す。フィルタは Step 3。
    course = courses[0]

    return render_template("result.html", course=course, weather=weather)
```

### templates/index.html

```html
<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <title>半日おでかけコース</title>
</head>
<body>
  <h1>今日、どう過ごす？</h1>

  <form action="/suggest" method="post">
    <label>
      今の気分（自由に書いてOK）<br>
      <textarea name="free_text" rows="3" cols="40"
        placeholder="例: 疲れてる、あんまり歩きたくない"></textarea>
    </label>

    <p>
      空いてる時間:
      <label><input type="radio" name="duration" value="short"> 2時間くらい</label>
      <label><input type="radio" name="duration" value="half" checked> 半日</label>
    </p>

    <p>
      天気:
      <label><input type="radio" name="weather" value="sunny" checked> 晴れ</label>
      <label><input type="radio" name="weather" value="rainy"> 雨</label>
    </p>

    <button type="submit">コースを提案してもらう</button>
  </form>
</body>
</html>
```

### templates/result.html

```html
<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <title>{{ course.name }}</title>
</head>
<body>
  <h1>{{ course.name }}</h1>
  <p>{{ course.description }}</p>

  <p>
    エリア: {{ course.area }} /
    所要: {{ course.total_duration_min }}分 /
    費用目安: {{ course.total_cost_yen }}円
  </p>

  <p>
    {% if course.indoor_only %}<span>全部屋内</span>{% endif %}
    {% if course.solo_friendly %}<span>1人向け</span>{% endif %}
    <span>天気: {{ weather }}</span>
  </p>

  <h2>行程</h2>
  <ol>
    {% for spot in course.spots %}
      <li>
        <strong>{{ spot.time }} {{ spot.name }}</strong>({{ spot.stay_min }}分)<br>
        {{ spot.note }}
      </li>
    {% endfor %}
  </ol>

  <p><a href="/">戻る</a></p>
</body>
</html>
```

## 動作確認

```bash
uv run flask --app app run --debug
```

`--debug` を付けるとファイル保存で自動リロード + エラー画面が見やすくなる。開発中は必ず付ける。

1. `http://localhost:5000` を開く
2. フォームに何か入れて「提案してもらう」
3. `courses.json` の1件目が表示される

## Jinja2 の記法（ハマりポイント）

Flask のテンプレートは **Jinja2** という記法。Python に似てるが微妙に違う。

| やりたいこと | 書き方 |
|---|---|
| 変数を出力 | `{{ course.name }}` |
| if 文 | `{% if course.indoor_only %} ... {% endif %}` |
| for 文 | `{% for spot in course.spots %} ... {% endfor %}` |

- `{{ ... }}` は「値を表示」、`{% ... %}` は「制御構文」
- `endif` / `endfor` を忘れると壊れる（Python のインデントで閉じない）

## つまずきポイント

### `TemplateNotFound`
`templates/` フォルダの名前が違う or 場所が違う。`app.py` と同じ階層に `templates/` を作ること。

### フォーム送信で 405 Method Not Allowed
`@app.route("/suggest", methods=["POST"])` の `methods=["POST"]` を忘れてる。デフォルトは GET のみ。

### `request.form.get("...")` が None になる
HTML の `<input name="...">` の name と、Python 側の get の文字列が一致してないと取れない。

### JSON の読み込みでファイルが見つからない
Flask を起動したディレクトリが `courses.json` と同じ場所である必要がある。プロジェクトルートで起動すること。

## 完了チェック
- [ ] `/` でフォームが表示される
- [ ] 送信すると `courses.json` の1件目が表示される
- [ ] 表示ページに「戻る」リンクがあり、フォームに戻れる
- [ ] `--debug` モードで起動できて、HTML を編集して保存するとリロードで反映される
