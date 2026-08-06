# Step 1. コースデータを作る

## ゴール
- `courses.json` に手書きでコース5件を用意する
- Python スクリプトで読み込んで、内容を print できる

## 触るファイル
- `courses.json`（新規作成）
- `load_courses.py`（新規作成、動作確認用の使い捨てスクリプト）

## なぜ JSON なのか

要件書では `spots.json` にスポットを持ち、LLM に組み立てさせる設計だった。
MVP では **組み立て済みのコース** を JSON に持つので、ファイル名は `courses.json` とする。

- データベース（SQLite など）は不要。ファイル1個で完結する方が管理がラク
- JSON は Python 標準の `json` モジュールで読める。追加インストール不要

## コースの構造

1つのコース = 2〜3スポットを繋いだ半日プラン。以下の項目を持つ。

| 項目 | 例 | 用途 |
|---|---|---|
| `id` | `"cafe_book_ikebukuro"` | 内部識別。英数字とアンダースコアだけで書く |
| `name` | `"本と珈琲でだらだら池袋"` | 表示（Step 4 で LLM に上書きさせる。今は仮でOK） |
| `description` | `"歩き回らずゆっくり過ごす3時間半"` | 表示（同上） |
| `area` | `"池袋"` | 表示のみ。MVP は1エリア固定 |
| `total_duration_min` | `210` | フィルタ用（3.5時間 = 210分） |
| `total_cost_yen` | `2500` | 表示 |
| `indoor_only` | `true` / `false` | フィルタ用（雨の日は `true` のみ通す） |
| `solo_friendly` | `true` / `false` | フィルタ用 |
| `energy_level` | `"low"` / `"mid"` / `"high"` | フィルタ用（「疲れてる」= `low` を出す） |
| `spots` | 配列（下記） | 表示 |

`spots` の各要素:

| 項目 | 例 |
|---|---|
| `time` | `"13:00"` |
| `name` | `"梟書茶房"` |
| `stay_min` | `90` |
| `note` | `"長居OKな喫茶。窓際が空きやすい"` |

### courses.json のサンプル（1件だけ抜粋）

これをコピーして自分の街のスポットで置き換えて OK。まずは1件だけ書いてみて、動くのを確認してから5件に増やすと詰まりにくい。

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
      {
        "time": "13:00",
        "name": "梟書茶房",
        "stay_min": 90,
        "note": "長居OKな喫茶。窓際が空きやすい"
      },
      {
        "time": "14:45",
        "name": "ジュンク堂書店 池袋本店",
        "stay_min": 75,
        "note": "9階まである日本最大級。座り読みOK"
      },
      {
        "time": "16:15",
        "name": "タリーズコーヒー 池袋東口店",
        "stay_min": 45,
        "note": "買った本を眺めながらひと休み"
      }
    ]
  }
]
```

## 作る5件のバリエーション例

Step 3 のフィルタで意味を持つよう、以下のように **属性の違うコース** を混ぜること。全部同じ属性だと切替が効かない。

| # | イメージ | indoor | energy | 使いどころ |
|---|---|---|---|---|
| 1 | 本と喫茶 | true | low | 疲れてる／雨の日 |
| 2 | 公園散歩＋カフェ | false | mid | 元気で晴れ |
| 3 | 美術館＋物販＋カフェ | true | mid | 雨だがちょい動きたい |
| 4 | 商店街食べ歩き | false | high | 元気で晴れ／食欲あり |
| 5 | 映画＋ごはん | true | low | 雨・疲れてる・夜まで |

## 読み込みスクリプト（load_courses.py）

JSON が正しく書けているか確認するための使い捨てスクリプト。動いたら消してよい。

```python
import json

with open("courses.json", encoding="utf-8") as f:
    courses = json.load(f)

print(f"読み込んだコース数: {len(courses)}")
print()

for course in courses:
    print(f"■ {course['name']} ({course['area']})")
    print(f"  時間: {course['total_duration_min']}分 / 費用: {course['total_cost_yen']}円")
    print(f"  屋内のみ: {course['indoor_only']} / 疲労度: {course['energy_level']}")
    for spot in course["spots"]:
        print(f"    {spot['time']} {spot['name']} ({spot['stay_min']}分)")
    print()
```

実行:

```bash
uv run python load_courses.py
```

## つまずきポイント

### JSON の書式エラー
- 末尾カンマ禁止（`{"a": 1,}` は NG）
- キーは必ずダブルクォート（シングルクォート `'a'` は NG）
- 真偽値は `true` / `false`（Python の `True` / `False` ではない、先頭小文字）
- 保存時に文字コードは UTF-8

エラーが出たら [JSONLint](https://jsonlint.com/) にコピペすると、何行目が悪いか教えてくれる。

### `FileNotFoundError`
`load_courses.py` を実行するディレクトリが `courses.json` と同じ場所である必要がある。プロジェクトのルート（`app.py` があるディレクトリ）で実行すること。

### `encoding="utf-8"` を忘れる
Windows で書いた場合、これを付けないと日本語が化けたり `UnicodeDecodeError` になる。Mac/Linux でも常に付けておくのが安全。

## 完了チェック
- [ ] `courses.json` に5件のコースが書かれている
- [ ] `uv run python load_courses.py` を実行すると、5件全部が print される
- [ ] 5件の中に `indoor_only: true` が最低2件、`false` が最低1件ある
- [ ] 5件の中に `energy_level` が `low` / `mid` / `high` それぞれ1件以上ある
