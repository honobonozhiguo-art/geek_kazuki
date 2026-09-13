import json

with open("courses.json", encoding="utf-8") as f:
    courses = json.load(f)

print(f"読み込んだコース数: {len(courses)}")