# backend/ocr.py
import base64, json, os
from pathlib import Path
from openai import OpenAI

def _get_client():
    api_key = os.environ.get("DASHSCOPE_API_KEY")
    if not api_key:
        raise RuntimeError("DASHSCOPE_API_KEY 环境变量未设置")
    return OpenAI(
        api_key=api_key,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    )

PROMPT = """这是一本书的封面照片。请提取以下信息并以 JSON 格式返回：
{
  "title": "书名（如果有副标题也包含）",
  "author": "作者姓名",
  "publisher": "出版社（如果可见，否则为空字符串）",
  "confidence": "high/medium/low"
}
只返回 JSON，不要其他文字。"""

def extract_book_info(image_path: str) -> dict:
    if not os.path.exists(image_path):
        return {"error": f"文件不存在: {image_path}"}
    try:
        with open(image_path, "rb") as f:
            image_data = base64.standard_b64encode(f.read()).decode("utf-8")
        ext = Path(image_path).suffix.lower().replace(".", "")
        mime = "image/jpeg" if ext in ["jpg", "jpeg"] else f"image/{ext}"
        client = _get_client()
        response = client.chat.completions.create(
            model="qwen-vl-plus",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{image_data}"}},
                    {"type": "text", "text": PROMPT}
                ]
            }]
        )
        raw = response.choices[0].message.content.strip()
        clean = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(clean)
    except json.JSONDecodeError as e:
        return {"error": f"JSON解析失败: {e}", "raw": raw}
    except Exception as e:
        return {"error": str(e)}

def extract_book_info_from_base64(image_b64: str, mime_type: str = "image/jpeg") -> dict:
    try:
        client = _get_client()
        response = client.chat.completions.create(
            model="qwen-vl-plus",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{image_b64}"}},
                    {"type": "text", "text": PROMPT}
                ]
            }]
        )
        raw = response.choices[0].message.content.strip()
        clean = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(clean)
    except Exception as e:
        return {"error": str(e)}
