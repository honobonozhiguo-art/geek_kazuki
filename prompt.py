import json
import os

from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

SYSTEM_PROMPT = """あなたは半日おでかけコースを紹介するコピーライターです。
入力として渡されるコースの内容を元に、以下のJSONのみを返してください。
前置き・説明・コードフェンスは一切つけない。
{
  "name": "コース名(20文字以内)",
  "description": "一言説明(40文字以内、体言止めか常体)"
}
"""


def generate_naming(course: dict, free_text: str, weather: str) -> dict:
    user_content = f"""ユーザーの気分: {free_text or "特になし"}
天気: {"雨" if weather == "rainy" else "晴れ"}
エリア: {course["area"]}
スポット: {", ".join(s["name"] for s in course["spots"])}
所要時間: {course["total_duration_min"]}分
"""

    try:
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=SYSTEM_PROMPT + "\n\n" + user_content,
        )

        text = response.text.strip()
        data = json.loads(text)

        if "name" in data and "description" in data:
            return data

        print(f"[warn] Gemini応答に必須キーがない: {data}")
        return None

    except json.JSONDecodeError as e:
        print(f"[warn] Gemini応答がJSONではない: {e}")
        return None

    except Exception as e:
        print(f"[warn] Gemini呼び出し失敗: {e}")
        return None