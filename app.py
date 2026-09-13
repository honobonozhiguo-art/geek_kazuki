import json
from flask import Flask, render_template, request
from prompt import generate_naming

app = Flask(__name__)


def load_courses():
    with open("courses.json", encoding="utf-8") as f:
        return json.load(f)


LOW_WORDS = ["疲れ", "だるい", "歩きたくない", "ゆっくり", "のんびり"]

HIGH_WORDS = ["元気", "がっつり", "動きたい", "たくさん"]


def guess_energy(free_text: str) -> str:
    text = free_text.lower()

    if any(w in text for w in LOW_WORDS):
        return "low"

    if any(w in text for w in HIGH_WORDS):
        return "high"

    return "mid"


def pick_course(courses, weather, duration, energy, excluded_ids=None):
    excluded_ids = excluded_ids or []

    candidates = [c for c in courses if c["id"] not in excluded_ids]

    if weather == "rainy":
        candidates = [c for c in candidates if c["indoor_only"]]

    if duration == "short":
        candidates = [
            c for c in candidates
            if c["total_duration_min"] <= 150
        ]

    if not candidates:
        return None

    preferred = [
        c for c in candidates
        if c["energy_level"] == energy
    ]

    return preferred[0] if preferred else candidates[0]


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/suggest", methods=["POST"])
@app.route("/suggest", methods=["POST"])
def suggest():
    print("★★ suggestが実行された ★★")

    free_text = request.form.get("free_text", "")
    duration = request.form.get("duration", "half")
    weather = request.form.get("weather", "sunny")

    excluded_raw = request.form.get("excluded", "")
    excluded_ids = [x for x in excluded_raw.split(",") if x]

    courses = load_courses()

    energy = guess_energy(free_text)

    course = pick_course(
        courses,
        weather,
        duration,
        energy,
        excluded_ids
    )

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

    next_excluded = ",".join(excluded_ids + [course["id"]])

    remaining = max(0, 3 - len(excluded_ids))

    return render_template(
        "result.html",
        course=course,
        weather=weather,
        matched_energy=energy,
        used_ai=used_ai,
        free_text=free_text,
        duration=duration,
        next_excluded=next_excluded,
        remaining=remaining,
    )