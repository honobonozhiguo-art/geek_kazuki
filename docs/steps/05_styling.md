# Step 5. 見た目を整える

## ゴール
- `static/style.css` を追加してデモに耐える見た目にする
- 1画面で完結（要件書 §2）していることが視覚的にわかる
- スマホ幅でも崩れない（プレゼンター/観客がスマホで見る可能性）

## 触るファイル
- `static/style.css`（新規）
- `templates/base.html`（新規、共通レイアウト）
- `templates/index.html`（`base.html` を継承する形に書き換え）
- `templates/result.html`（同上）

## 前提コード

このステップを始める時点の `templates/index.html`:

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
    <!-- ... フォーム本体 ... -->
  </form>
</body>
</html>
```

このステップを始める時点の `templates/result.html`:

```html
<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <title>{{ course.name }}</title>
</head>
<body>
  <h1>{{ course.name }}</h1>
  <!-- ... コース表示 ... -->
</body>
</html>
```

## 方針

- **CSS フレームワークは使わない**。素の CSS で書く（要件書 §5「CSS フレームワーク1つ」だが、MVP では入れるより素で書いた方が早い）
- **色数は絞る**。背景・文字・アクセントの3色まで
- **カードデザイン1つで勝負**。コースを1枚のカードに収める（要件書 §4.2）
- **フォントは system-ui**。読み込み待ちがなく、OS 標準のきれいなフォントが使える

## 実装

### templates/base.html（新規）

共通レイアウトを1ファイルにまとめる。各ページはこれを継承する。

```html
<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{% block title %}半日おでかけコース{% endblock %}</title>
  <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
</head>
<body>
  <main class="container">
    {% block content %}{% endblock %}
  </main>
</body>
</html>
```

### templates/index.html（書き換え）

```html
{% extends "base.html" %}
{% block title %}今日、どう過ごす？{% endblock %}
{% block content %}
  <h1>今日、どう過ごす？</h1>
  <p class="lead">気分と天気を入れるだけ。3タップで半日の予定が決まる。</p>

  <form action="/suggest" method="post" class="form">
    <label class="field">
      <span class="field-label">今の気分</span>
      <textarea name="free_text" rows="3"
        placeholder="例: 疲れてる、あんまり歩きたくない"></textarea>
    </label>

    <fieldset class="field">
      <legend class="field-label">空いてる時間</legend>
      <label class="chip"><input type="radio" name="duration" value="short"> 2時間</label>
      <label class="chip"><input type="radio" name="duration" value="half" checked> 半日</label>
    </fieldset>

    <fieldset class="field">
      <legend class="field-label">天気</legend>
      <label class="chip"><input type="radio" name="weather" value="sunny" checked> 晴れ</label>
      <label class="chip"><input type="radio" name="weather" value="rainy"> 雨</label>
    </fieldset>

    <button type="submit" class="button-primary">コースを提案してもらう</button>
  </form>
{% endblock %}
```

### templates/result.html（書き換え）

```html
{% extends "base.html" %}
{% block title %}{{ course.name }}{% endblock %}
{% block content %}
  <article class="card">
    <header class="card-head">
      <h1>{{ course.name }}</h1>
      <p class="card-lead">{{ course.description }}</p>
      <div class="badges">
        {% if course.indoor_only %}<span class="badge">全部屋内</span>{% endif %}
        {% if course.solo_friendly %}<span class="badge">1人向け</span>{% endif %}
        <span class="badge">{{ "雨の日" if weather == "rainy" else "晴れの日" }}</span>
      </div>
    </header>

    <dl class="stats">
      <div><dt>所要</dt><dd>{{ course.total_duration_min }}分</dd></div>
      <div><dt>費用目安</dt><dd>{{ course.total_cost_yen }}円</dd></div>
      <div><dt>エリア</dt><dd>{{ course.area }}</dd></div>
    </dl>

    <ol class="timeline">
      {% for spot in course.spots %}
        <li class="timeline-item">
          <div class="timeline-time">{{ spot.time }}</div>
          <div class="timeline-body">
            <div class="timeline-name">{{ spot.name }}</div>
            <div class="timeline-meta">{{ spot.stay_min }}分</div>
            <div class="timeline-note">{{ spot.note }}</div>
          </div>
        </li>
      {% endfor %}
    </ol>

    {% if used_ai %}
      <p class="ai-note">コース名は AI が今日の気分に合わせて生成しました</p>
    {% endif %}
  </article>

  <p class="back"><a href="/">別の条件で試す</a></p>
{% endblock %}
```

### static/style.css（新規）

```css
:root {
  --bg: #fafaf7;
  --fg: #1a1a1a;
  --muted: #666;
  --accent: #e05a3a;
  --line: #e4e2dc;
  --card-bg: #fff;
}

* { box-sizing: border-box; }

body {
  margin: 0;
  font-family: system-ui, -apple-system, "Hiragino Sans", "Yu Gothic", sans-serif;
  background: var(--bg);
  color: var(--fg);
  line-height: 1.6;
}

.container {
  max-width: 560px;
  margin: 0 auto;
  padding: 24px 16px 60px;
}

h1 {
  font-size: 1.6rem;
  margin: 0 0 8px;
}

.lead {
  color: var(--muted);
  margin: 0 0 24px;
}

/* フォーム */
.form { display: flex; flex-direction: column; gap: 20px; }
.field { display: block; border: none; padding: 0; margin: 0; }
.field-label {
  display: block;
  font-weight: 600;
  margin-bottom: 8px;
  font-size: 0.95rem;
}

textarea {
  width: 100%;
  padding: 12px;
  border: 1px solid var(--line);
  border-radius: 8px;
  font: inherit;
  resize: vertical;
}

.chip {
  display: inline-block;
  padding: 8px 14px;
  margin-right: 8px;
  border: 1px solid var(--line);
  border-radius: 999px;
  cursor: pointer;
  user-select: none;
}
.chip input { margin-right: 6px; }

.button-primary {
  padding: 14px 20px;
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
}
.button-primary:hover { opacity: 0.9; }

/* カード */
.card {
  background: var(--card-bg);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 24px;
  margin-top: 12px;
}
.card-head h1 { margin-bottom: 4px; }
.card-lead { color: var(--muted); margin: 0 0 16px; }

.badges { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 20px; }
.badge {
  font-size: 0.8rem;
  padding: 3px 10px;
  background: var(--bg);
  border: 1px solid var(--line);
  border-radius: 999px;
  color: var(--muted);
}

.stats {
  display: flex;
  gap: 24px;
  padding: 12px 0;
  margin: 0 0 20px;
  border-top: 1px solid var(--line);
  border-bottom: 1px solid var(--line);
}
.stats > div { flex: 1; }
.stats dt { font-size: 0.75rem; color: var(--muted); margin: 0; }
.stats dd { font-size: 1rem; font-weight: 600; margin: 2px 0 0; }

/* タイムライン */
.timeline { list-style: none; padding: 0; margin: 0; }
.timeline-item {
  display: flex;
  gap: 14px;
  padding: 14px 0;
  border-top: 1px dashed var(--line);
}
.timeline-item:first-child { border-top: none; }
.timeline-time {
  flex: 0 0 55px;
  font-weight: 600;
  color: var(--accent);
}
.timeline-body { flex: 1; }
.timeline-name { font-weight: 600; }
.timeline-meta { font-size: 0.8rem; color: var(--muted); }
.timeline-note { font-size: 0.9rem; margin-top: 4px; }

.ai-note {
  font-size: 0.8rem;
  color: var(--muted);
  margin-top: 20px;
  text-align: right;
}

.back { margin-top: 16px; text-align: center; }
.back a { color: var(--accent); }
```

## Jinja2 のテンプレート継承（初めての人向け）

`{% extends "base.html" %}` は「このファイルは `base.html` をベースにする」の意味。
`{% block content %}...{% endblock %}` は `base.html` の同名 block を差し替える。

これで各ページに `<html>` `<head>` を書かなくて済む。**共通の変更（例: CSS ファイルの追加）が1箇所で終わる**。

## 動作確認

```bash
uv run flask --app app run --debug
```

- CSS が反映されない時はブラウザで **Cmd+Shift+R**（強制リロード）
- スマホ幅で見たい時は Chrome の DevTools → 左上の端末アイコンでレスポンシブモード

## つまずきポイント

### CSS が反映されない
- `static/` フォルダの名前が違う（`css/` などにしていない？）
- `{{ url_for('static', filename='style.css') }}` の書き方ミス
- ブラウザキャッシュ → 強制リロードで解決

### `TemplateNotFound: base.html`
- `templates/base.html` が正しい場所にあるか確認
- `{% extends "base.html" %}` のクォート内をタイポしてないか

### モバイルで文字が小さい
- `<meta name="viewport" content="width=device-width, initial-scale=1">` を head に入れているか（`base.html` にはすでに入れてある）

## デザインの調整余地（時間があれば）

- アクセント色 `--accent` を変えるだけで印象が変わる（例: `#3a7ae0` で青系、`#4a8f4a` で緑系）
- `font-family` に Google Fonts を足すと雰囲気が出る（が、読み込み時間が増えるのでデモ環境で試してから）

**やらないほうがいいこと**:
- CSS フレームワークの後付け導入（既存のクラス名と衝突する）
- 過剰なアニメーション（デモの動作を遅く感じさせる）

## 完了チェック
- [ ] `/` を開くと、フォームが縦に並んで見やすい
- [ ] `/suggest` の結果がカード状にまとまり、タイムラインで行程が見える
- [ ] スマホ幅（375px）で崩れない
- [ ] 「別の条件で試す」でフォームに戻れる
