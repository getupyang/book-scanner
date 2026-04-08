# Book Scanner Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 手机打开网页 → 拍书封面 → 10秒内看到豆瓣评分和热门短评

**Architecture:** 单页 PWA 前端（Vercel 托管）调用 FastAPI 后端（Railway 托管）；后端并行执行 Qwen-VL 图像识别和豆瓣网页解析，返回结构化 JSON；前端单页内切换状态（拍照→loading→结果），无页面跳转。

**Tech Stack:** Python 3.11 + FastAPI + httpx（后端）/ 原生 HTML+CSS+JS 单文件（前端）/ 阿里云 DashScope Qwen-VL-max（OCR）/ 豆瓣网页解析（无需 API key）/ Railway（后端部署）/ Vercel（前端部署）

---

## 文件结构

```
book-scanner/
├── backend/
│   ├── main.py              # FastAPI 入口，路由定义
│   ├── ocr.py               # Qwen-VL 图像识别
│   ├── douban.py            # 豆瓣搜索+详情页解析
│   ├── requirements.txt     # 依赖
│   ├── Procfile             # Railway 启动命令
│   └── .env                 # 本地开发环境变量（不提交）
├── frontend/
│   └── index.html           # 单文件 PWA（含 CSS+JS）
│   └── manifest.json        # PWA manifest
├── tests/
│   ├── test_ocr.py          # OCR 模块测试
│   ├── test_douban.py       # 豆瓣解析测试
│   └── test_e2e.py          # 端到端集成测试
├── docs/
│   └── plans/
│       └── 2026-04-08-book-scanner-phase1.md  # 本文件
└── spike_ocr.py             # 已验证，可参考调用方式
└── spike_douban.py          # 已验证，可参考解析逻辑
```

---

## Task 1: 初始化项目结构

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/.env`（本地用，不提交）
- Create: `.gitignore`

- [ ] **Step 1: 创建目录结构**

```bash
cd /Users/getupyang/Documents/ai/coding/book-scanner
mkdir -p backend frontend tests
```

- [ ] **Step 2: 创建 requirements.txt**

```
# backend/requirements.txt
fastapi==0.115.0
uvicorn==0.30.0
httpx==0.27.0
openai==1.40.0
python-multipart==0.0.9
```

- [ ] **Step 3: 创建 .env（本地开发用）**

```bash
# backend/.env
DASHSCOPE_API_KEY=sk-6396906889714bfbb54b7ea67c4e542e
```

- [ ] **Step 4: 创建 .gitignore**

```
# .gitignore
backend/.env
__pycache__/
*.pyc
.DS_Store
```

- [ ] **Step 5: 安装依赖**

```bash
cd backend
pip install -r requirements.txt
```

Expected: 所有包安装成功，无报错

- [ ] **Step 6: git init 并首次提交**

```bash
cd /Users/getupyang/Documents/ai/coding/book-scanner
git init
git add requirements.txt .gitignore docs/
git commit -m "chore: init book-scanner project structure"
```

---

## Task 2: OCR 模块（Qwen-VL 识别书封面）

**Files:**
- Create: `backend/ocr.py`
- Create: `tests/test_ocr.py`

- [ ] **Step 1: 写测试（先写，后实现）**

```python
# tests/test_ocr.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import pytest
from ocr import extract_book_info

def test_returns_dict_with_required_keys():
    """返回值必须包含 title, author, confidence 三个 key"""
    # 用测试图路径（已验证过的图）
    img_path = "/Users/getupyang/Documents/ai/coding/book-scanner/testpic/微信图片_20260408112019_93_1.jpg"
    result = extract_book_info(img_path)
    assert isinstance(result, dict)
    assert "title" in result
    assert "author" in result
    assert "confidence" in result

def test_recognizes_shijian_de_zhixu():
    """能正确识别《时间的秩序》"""
    img_path = "/Users/getupyang/Documents/ai/coding/book-scanner/testpic/微信图片_20260408112019_93_1.jpg"
    result = extract_book_info(img_path)
    assert "时间" in result["title"]

def test_recognizes_wanganshe_zhuan():
    """能正确识别《王安石传》"""
    img_path = "/Users/getupyang/Documents/ai/coding/book-scanner/testpic/微信图片_20260408112020_94_1.jpg"
    result = extract_book_info(img_path)
    assert "王安石" in result["title"]

def test_handles_missing_file():
    """文件不存在时返回 error 字段"""
    result = extract_book_info("/nonexistent/path.jpg")
    assert "error" in result
```

- [ ] **Step 2: 运行测试，确认全部失败**

```bash
cd /Users/getupyang/Documents/ai/coding/book-scanner
python -m pytest tests/test_ocr.py -v
```

Expected: 4 个测试全部 FAIL（ImportError: No module named 'ocr'）

- [ ] **Step 3: 实现 ocr.py**

```python
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
    """
    从书封面图片提取书名和作者。
    返回: {"title": str, "author": str, "publisher": str, "confidence": str}
    失败时返回: {"error": str}
    """
    if not os.path.exists(image_path):
        return {"error": f"文件不存在: {image_path}"}

    try:
        with open(image_path, "rb") as f:
            image_data = base64.standard_b64encode(f.read()).decode("utf-8")

        ext = Path(image_path).suffix.lower().replace(".", "")
        mime = "image/jpeg" if ext in ["jpg", "jpeg"] else f"image/{ext}"

        client = _get_client()
        response = client.chat.completions.create(
            model="qwen-vl-max-latest",
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
    """
    从 base64 字符串提取书名和作者（供 API 调用）。
    """
    try:
        client = _get_client()
        response = client.chat.completions.create(
            model="qwen-vl-max-latest",
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
```

- [ ] **Step 4: 运行测试，确认通过**

```bash
python -m pytest tests/test_ocr.py -v
```

Expected: 4 个测试全部 PASS（会真实调用 API，需要约 5-10 秒）

- [ ] **Step 5: 提交**

```bash
git add backend/ocr.py tests/test_ocr.py
git commit -m "feat: add Qwen-VL OCR module for book cover recognition"
```

---

## Task 3: 豆瓣解析模块

**Files:**
- Create: `backend/douban.py`
- Create: `tests/test_douban.py`

- [ ] **Step 1: 写测试**

```python
# tests/test_douban.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import pytest
from douban import search_book, get_book_detail

def test_search_returns_score():
    """搜索《时间的秩序》应返回评分 > 0"""
    result = search_book("时间的秩序", "卡洛·罗韦利")
    assert result is not None
    assert "score" in result
    assert float(result["score"]) > 0

def test_search_returns_votes():
    """搜索应返回评分人数"""
    result = search_book("时间的秩序", "卡洛·罗韦利")
    assert "votes" in result
    assert int(result["votes"]) > 1000

def test_search_returns_subject_id():
    """搜索应返回 subject_id 用于后续查详情"""
    result = search_book("时间的秩序", "卡洛·罗韦利")
    assert "subject_id" in result
    assert result["subject_id"]  # 非空

def test_get_detail_returns_pub_year():
    """详情页应返回出版年份"""
    result = get_book_detail("33424487")  # 时间的秩序的 ID
    assert "pub_year" in result
    assert result["pub_year"] == "2019"

def test_get_detail_returns_comments():
    """详情页应返回至少 1 条短评"""
    result = get_book_detail("33424487")
    assert "comments" in result
    assert len(result["comments"]) >= 1

def test_search_not_found_returns_none():
    """搜索不存在的书返回 None"""
    result = search_book("xyzxyzxyz完全不存在的书名123456", "")
    assert result is None
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
python -m pytest tests/test_douban.py -v
```

Expected: 全部 FAIL（ImportError）

- [ ] **Step 3: 实现 douban.py**

```python
# backend/douban.py
import urllib.request, urllib.parse, re
from typing import Optional

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Accept-Encoding": "identity",
}

def _fetch(url: str) -> Optional[str]:
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.read().decode("utf-8", errors="ignore")
    except Exception:
        return None

def search_book(title: str, author: str = "") -> Optional[dict]:
    """
    搜索豆瓣，返回第一条结果的评分信息。
    返回: {"subject_id", "title", "score", "votes", "pub_year", "author"} 或 None
    """
    q = urllib.parse.quote(f"{title} {author}".strip())
    url = f"https://www.douban.com/search?cat=1001&q={q}"
    body = _fetch(url)
    if not body:
        return None

    # 从搜索结果区域提取
    section = body[body.find('search-result'):][:10000]

    # 提取第一个 subject_id
    id_match = re.search(r'subject[/=](\d{6,})', section)
    if not id_match:
        return None
    subject_id = id_match.group(1)

    # 提取书名
    title_match = re.search(r'class="title"[^>]*>.*?<a[^>]+>([^<]+)</a>', section, re.DOTALL)
    found_title = title_match.group(1).strip() if title_match else title

    # 提取评分
    score_match = re.search(r'class="rating_nums">([\d.]+)</span>', section)
    score = score_match.group(1) if score_match else "0"

    # 提取评分人数
    votes_match = re.search(r'\((\d+)人评价\)', section)
    votes = votes_match.group(1) if votes_match else "0"

    # 提取出版年
    cast_match = re.search(r'class="subject-cast"[^>]*>(.*?)</span>', section, re.DOTALL)
    pub_year = ""
    if cast_match:
        year_match = re.search(r'(\d{4})', cast_match.group(1))
        pub_year = year_match.group(1) if year_match else ""

    if score == "0" and votes == "0":
        return None

    return {
        "subject_id": subject_id,
        "title": found_title,
        "score": score,
        "votes": votes,
        "pub_year": pub_year,
        "douban_url": f"https://book.douban.com/subject/{subject_id}/",
    }

def get_book_detail(subject_id: str, delay: float = 0.5) -> dict:
    """delay: 避免高频请求被豆瓣封，默认 0.5 秒"""
    import time
    time.sleep(delay)
    """
    抓取书籍详情页，返回出版年份和热门短评。
    返回: {"pub_year": str, "comments": [str]}
    """
    url = f"https://book.douban.com/subject/{subject_id}/"
    body = _fetch(url)
    if not body:
        return {"pub_year": "", "comments": []}

    # 出版年
    pub_year = ""
    year_match = re.search(r'出版年.*?(\d{4})', body)
    if year_match:
        pub_year = year_match.group(1)

    # 短评（详情页通常有 4-6 条）
    comments = re.findall(r'<span class="short">(.*?)</span>', body)
    # 过滤掉简介（通常是最后一条，比较长）
    comments = [c for c in comments if len(c) < 200]

    return {
        "pub_year": pub_year,
        "comments": comments[:5],
    }
```

- [ ] **Step 4: 运行测试**

```bash
python -m pytest tests/test_douban.py -v
```

Expected: 全部 PASS（会真实请求豆瓣，约 3-5 秒）

- [ ] **Step 5: 提交**

```bash
git add backend/douban.py tests/test_douban.py
git commit -m "feat: add Douban scraper for ratings and reviews"
```

---

## Task 3.5: 端到端集成测试

**Files:**
- Create: `tests/test_e2e.py`

- [ ] **Step 1: 写集成测试**

```python
# tests/test_e2e.py
"""
端到端测试：OCR → 豆瓣搜索 → 详情，验证全链路
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from ocr import extract_book_info
from douban import search_book, get_book_detail

def test_full_pipeline_shijian():
    """《时间的秩序》完整链路：识别 → 搜索 → 拿到评分"""
    img_path = "/Users/getupyang/Documents/ai/coding/book-scanner/testpic/微信图片_20260408112019_93_1.jpg"
    
    # Step 1: OCR
    ocr = extract_book_info(img_path)
    assert "error" not in ocr, f"OCR 失败: {ocr}"
    assert "时间" in ocr["title"]
    
    # Step 2: 豆瓣搜索
    douban = search_book(ocr["title"], ocr.get("author", ""))
    assert douban is not None, "豆瓣搜索失败"
    assert float(douban["score"]) > 8.0
    
    # Step 3: 详情
    detail = get_book_detail(douban["subject_id"])
    assert len(detail["comments"]) >= 1
    assert detail["pub_year"] == "2019"

def test_full_pipeline_wanganshe():
    """《王安石传》完整链路"""
    img_path = "/Users/getupyang/Documents/ai/coding/book-scanner/testpic/微信图片_20260408112020_94_1.jpg"
    
    ocr = extract_book_info(img_path)
    assert "error" not in ocr
    assert "王安石" in ocr["title"]
    
    douban = search_book(ocr["title"], ocr.get("author", ""))
    assert douban is not None
    assert float(douban["score"]) > 0
```

- [ ] **Step 2: 运行，确认通过**

```bash
python -m pytest tests/test_e2e.py -v
```

Expected: 2 个测试 PASS（约 15-20 秒，真实调用 API + 豆瓣）

- [ ] **Step 3: 提交**

```bash
git add tests/test_e2e.py
git commit -m "test: add end-to-end pipeline integration tests"
```

---

## Task 4: FastAPI 后端主程序

**Files:**
- Create: `backend/main.py`
- Create: `backend/Procfile`

- [ ] **Step 1: 实现 main.py**

```python
# backend/main.py
import asyncio, base64, os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from ocr import extract_book_info_from_base64
from douban import search_book, get_book_detail

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Phase 1 放开，Phase 2 收紧
    allow_methods=["*"],
    allow_headers=["*"],
)

class ScanRequest(BaseModel):
    image: str       # base64 编码的图片
    mime_type: str = "image/jpeg"

class ScanResponse(BaseModel):
    title: str
    author: str
    score: str
    votes: str
    pub_year: str
    comments: list[str]
    douban_url: str
    confidence: str
    ocr_error: str = ""
    douban_error: str = ""

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/scan", response_model=ScanResponse)
async def scan(req: ScanRequest):
    # Step 1: OCR 识别书名（同步，因为 openai SDK 是同步的）
    loop = asyncio.get_event_loop()
    ocr_result = await loop.run_in_executor(
        None, extract_book_info_from_base64, req.image, req.mime_type
    )

    if "error" in ocr_result:
        raise HTTPException(status_code=422, detail=f"OCR失败: {ocr_result['error']}")

    title = ocr_result.get("title", "")
    author = ocr_result.get("author", "")
    confidence = ocr_result.get("confidence", "low")

    if not title:
        raise HTTPException(status_code=422, detail="无法识别书名，请重新拍摄")

    # Step 2: 并行查豆瓣搜索 + 详情（搜索先跑，拿到 ID 再查详情）
    douban_error = ""
    score, votes, pub_year, comments, douban_url = "", "", "", [], ""

    search_result = await loop.run_in_executor(None, search_book, title, author)

    if search_result:
        subject_id = search_result["subject_id"]
        score = search_result["score"]
        votes = search_result["votes"]
        pub_year = search_result["pub_year"]
        douban_url = search_result["douban_url"]

        # 并行拉详情（主要是为了短评和更准确的出版年）
        detail = await loop.run_in_executor(None, get_book_detail, subject_id)
        comments = detail.get("comments", [])
        if not pub_year and detail.get("pub_year"):
            pub_year = detail["pub_year"]
    else:
        douban_error = "豆瓣未找到此书"

    return ScanResponse(
        title=title,
        author=author,
        score=score,
        votes=votes,
        pub_year=pub_year,
        comments=comments,
        douban_url=douban_url,
        confidence=confidence,
        douban_error=douban_error,
    )
```

- [ ] **Step 2: 创建 Procfile（Railway 部署用）**

```
# backend/Procfile
web: uvicorn main:app --host 0.0.0.0 --port $PORT
```

- [ ] **Step 3: 本地启动测试**

```bash
cd backend
uvicorn main:app --reload --port 8080
```

Expected: `Application startup complete` 无报错

- [ ] **Step 4: 测试 /health 接口**

```bash
curl http://localhost:8080/health
```

Expected: `{"status":"ok"}`

- [ ] **Step 5: 用测试图调用 /scan**

```bash
python3 - <<'EOF'
import base64, json, urllib.request

with open("/Users/getupyang/Documents/ai/coding/book-scanner/testpic/微信图片_20260408112019_93_1.jpg", "rb") as f:
    b64 = base64.b64encode(f.read()).decode()

data = json.dumps({"image": b64, "mime_type": "image/jpeg"}).encode()
req = urllib.request.Request(
    "http://localhost:8080/scan",
    data=data,
    headers={"Content-Type": "application/json"},
    method="POST"
)
with urllib.request.urlopen(req, timeout=30) as r:
    result = json.loads(r.read())
    print(json.dumps(result, ensure_ascii=False, indent=2))
EOF
```

Expected: 返回包含 title="时间的秩序"、score="8.9"、comments 非空的 JSON

- [ ] **Step 6: 提交**

```bash
git add backend/main.py backend/Procfile
git commit -m "feat: add FastAPI /scan endpoint with OCR + Douban pipeline"
```

---

## Task 5: 前端单页 PWA

**Files:**
- Create: `frontend/index.html`
- Create: `frontend/manifest.json`

> **注意：** 开发时把 `BACKEND_URL` 改为 `http://localhost:8080`，部署后改为 Railway 的地址。

### 5A: manifest + HTML 骨架

- [ ] **Step 1: 创建 manifest.json**

```json
{
  "name": "书店扫书",
  "short_name": "扫书",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#ffffff",
  "theme_color": "#1a1a2e",
  "icons": [
    {
      "src": "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>📚</text></svg>",
      "sizes": "any",
      "type": "image/svg+xml"
    }
  ]
}
```

- [ ] **Step 2: 创建 index.html 骨架（只有 HTML 结构，无 CSS/JS）**

```bash
# 验证骨架：浏览器打开 frontend/index.html，应看到三个 div（home/loading/result）都存在
```

### 5B: CSS 样式

- [ ] **Step 3: 把完整 CSS 填入 `<style>` 块**（见下方完整代码）

验证：手机浏览器访问，首屏看到居中的黑色圆形拍照按钮

### 5C: JS 交互逻辑

- [ ] **Step 4: 填入 `<script>` 块**（见下方完整代码）

验证：
- 点拍照按钮能唤起摄像头
- 选完图片出现 loading 屏
- `BACKEND_URL` 设为 localhost:8080 时，能拿到结果

---

### 完整 index.html 代码

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="default">
  <title>书店扫书</title>
  <link rel="manifest" href="manifest.json">
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", sans-serif;
      background: #f5f5f5;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
    }
    .screen { display: none; width: 100%; max-width: 480px; padding: 24px 16px; }
    .screen.active { display: flex; flex-direction: column; align-items: center; }

    /* 首屏 */
    #screen-home { justify-content: center; min-height: 100vh; gap: 24px; }
    .app-title { font-size: 24px; font-weight: 700; color: #1a1a2e; }
    .app-subtitle { font-size: 14px; color: #888; }
    .btn-camera {
      width: 160px; height: 160px; border-radius: 50%;
      background: #1a1a2e; border: none; cursor: pointer;
      display: flex; flex-direction: column; align-items: center;
      justify-content: center; gap: 8px; color: white;
    }
    .btn-camera svg { width: 48px; height: 48px; }
    .btn-camera span { font-size: 16px; }
    #file-input { display: none; }

    /* Loading 屏 */
    #screen-loading { justify-content: center; min-height: 100vh; gap: 16px; }
    .loading-step { font-size: 16px; color: #555; }
    .loading-step.done { color: #4CAF50; }
    .loading-step.active { color: #1a1a2e; font-weight: 600; }
    .spinner {
      width: 40px; height: 40px; border: 3px solid #eee;
      border-top-color: #1a1a2e; border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }
    @keyframes spin { to { transform: rotate(360deg); } }

    /* 结果屏 */
    #screen-result { gap: 16px; padding-bottom: 40px; }
    .book-header { width: 100%; background: white; border-radius: 16px; padding: 20px; }
    .book-title { font-size: 22px; font-weight: 700; color: #1a1a2e; margin-bottom: 4px; }
    .book-author { font-size: 14px; color: #666; margin-bottom: 12px; }
    .pub-year { font-size: 13px; color: #888; }
    .pub-year.old { color: #e67e22; font-weight: 600; }

    .score-card { width: 100%; background: white; border-radius: 16px; padding: 20px; text-align: center; }
    .score-number { font-size: 56px; font-weight: 800; color: #1a1a2e; line-height: 1; }
    .score-votes { font-size: 13px; color: #888; margin-top: 4px; }
    .score-na { font-size: 20px; color: #aaa; }

    .comments-card { width: 100%; background: white; border-radius: 16px; padding: 20px; }
    .card-title { font-size: 14px; font-weight: 600; color: #888; margin-bottom: 12px; }
    .comment-item {
      padding: 10px 0; border-bottom: 1px solid #f0f0f0;
      font-size: 14px; color: #333; line-height: 1.5;
    }
    .comment-item:last-child { border-bottom: none; }

    .error-card { width: 100%; background: #fff3f3; border-radius: 16px; padding: 20px; color: #c0392b; font-size: 14px; }

    .btn-retry {
      width: 100%; padding: 14px; border: 2px solid #1a1a2e;
      background: white; border-radius: 12px; font-size: 16px;
      cursor: pointer; color: #1a1a2e; font-weight: 600;
    }
    .btn-again {
      width: 100%; padding: 14px; background: #1a1a2e;
      border: none; border-radius: 12px; font-size: 16px;
      cursor: pointer; color: white; font-weight: 600;
    }
  </style>
</head>
<body>

<!-- 首屏 -->
<div id="screen-home" class="screen active">
  <div class="app-title">📚 书店扫书</div>
  <div class="app-subtitle">拍封面，看豆瓣评分</div>
  <button class="btn-camera" onclick="document.getElementById('file-input').click()">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>
      <circle cx="12" cy="13" r="4"/>
    </svg>
    <span>拍封面</span>
  </button>
  <input type="file" id="file-input" accept="image/*" capture="environment">
</div>

<!-- Loading 屏 -->
<div id="screen-loading" class="screen">
  <div class="spinner"></div>
  <div id="step-ocr" class="loading-step active">⏳ 正在识别书名...</div>
  <div id="step-douban" class="loading-step">　　查询豆瓣评分...</div>
</div>

<!-- 结果屏 -->
<div id="screen-result" class="screen">
  <div class="book-header">
    <div class="book-title" id="res-title"></div>
    <div class="book-author" id="res-author"></div>
    <div class="pub-year" id="res-year"></div>
  </div>

  <div class="score-card">
    <div id="res-score-container">
      <div class="score-number" id="res-score"></div>
      <div class="score-votes" id="res-votes"></div>
    </div>
  </div>

  <div class="comments-card" id="comments-section">
    <div class="card-title">豆瓣热门短评</div>
    <div id="res-comments"></div>
  </div>

  <div class="error-card" id="error-section" style="display:none"></div>

  <button class="btn-retry" onclick="retrySearch()">结果不对？手动输入书名</button>
  <button class="btn-again" onclick="goHome()">再拍一本</button>
</div>

<!-- 手动输入弹层（简单实现） -->
<div id="manual-overlay" style="display:none;position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.5);z-index:100;display:none;align-items:center;justify-content:center;">
  <div style="background:white;border-radius:16px;padding:24px;width:90%;max-width:400px;">
    <div style="font-size:16px;font-weight:600;margin-bottom:16px;">手动输入书名</div>
    <input id="manual-title" type="text" placeholder="书名" style="width:100%;padding:10px;border:1px solid #ddd;border-radius:8px;font-size:16px;margin-bottom:8px;">
    <input id="manual-author" type="text" placeholder="作者（可选）" style="width:100%;padding:10px;border:1px solid #ddd;border-radius:8px;font-size:16px;margin-bottom:16px;">
    <button onclick="submitManual()" style="width:100%;padding:14px;background:#1a1a2e;color:white;border:none;border-radius:12px;font-size:16px;cursor:pointer;">查询</button>
    <button onclick="closeManual()" style="width:100%;padding:14px;background:white;color:#666;border:1px solid #ddd;border-radius:12px;font-size:16px;cursor:pointer;margin-top:8px;">取消</button>
  </div>
</div>

<script>
// 开发时用 localhost，部署后替换为 Railway URL
const BACKEND_URL = "http://localhost:8080";

function showScreen(id) {
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  document.getElementById(id).classList.add('active');
}

function goHome() { showScreen('screen-home'); }

// 拍照触发
document.getElementById('file-input').addEventListener('change', async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  e.target.value = ''; // 允许重复拍同一张

  showScreen('screen-loading');
  document.getElementById('step-ocr').className = 'loading-step active';
  document.getElementById('step-douban').className = 'loading-step';

  const b64 = await fileToBase64(file);
  const mimeType = file.type || 'image/jpeg';

  try {
    document.getElementById('step-ocr').className = 'loading-step done';
    document.getElementById('step-douban').className = 'loading-step active';

    const resp = await fetch(`${BACKEND_URL}/scan`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image: b64, mime_type: mimeType })
    });

    if (!resp.ok) {
      const err = await resp.json();
      showError(err.detail || '识别失败，请重试');
      return;
    }

    const data = await resp.json();
    showResult(data);
  } catch (err) {
    showError('网络错误，请检查连接后重试');
  }
});

function fileToBase64(file) {
  return new Promise((resolve) => {
    const reader = new FileReader();
    reader.onload = (e) => resolve(e.target.result.split(',')[1]);
    reader.readAsDataURL(file);
  });
}

function showResult(data) {
  document.getElementById('res-title').textContent = data.title || '未知书名';
  document.getElementById('res-author').textContent = data.author ? `作者：${data.author}` : '';

  // 出版年份，超过10年加警告
  const yearEl = document.getElementById('res-year');
  if (data.pub_year) {
    const age = new Date().getFullYear() - parseInt(data.pub_year);
    yearEl.textContent = age > 10
      ? `⚠️ ${data.pub_year}年出版（${age}年前）`
      : `${data.pub_year}年出版`;
    yearEl.className = age > 10 ? 'pub-year old' : 'pub-year';
  }

  // 评分
  const scoreEl = document.getElementById('res-score');
  const votesEl = document.getElementById('res-votes');
  if (data.score && data.score !== '0') {
    scoreEl.textContent = data.score;
    votesEl.textContent = data.votes ? `${parseInt(data.votes).toLocaleString()} 人评分` : '';
  } else {
    document.getElementById('res-score-container').innerHTML = '<div class="score-na">豆瓣暂无评分</div>';
  }

  // 短评
  const commentsEl = document.getElementById('res-comments');
  if (data.comments && data.comments.length > 0) {
    commentsEl.innerHTML = data.comments
      .map(c => `<div class="comment-item">${c}</div>`)
      .join('');
    document.getElementById('comments-section').style.display = 'block';
  } else {
    document.getElementById('comments-section').style.display = 'none';
  }

  // 错误提示
  const errEl = document.getElementById('error-section');
  if (data.douban_error) {
    errEl.textContent = data.douban_error;
    errEl.style.display = 'block';
  } else {
    errEl.style.display = 'none';
  }

  showScreen('screen-result');
}

function showError(msg) {
  document.getElementById('res-title').textContent = '识别失败';
  document.getElementById('res-author').textContent = '';
  document.getElementById('res-year').textContent = '';
  document.getElementById('res-score-container').innerHTML = '';
  document.getElementById('comments-section').style.display = 'none';
  const errEl = document.getElementById('error-section');
  errEl.textContent = msg;
  errEl.style.display = 'block';
  showScreen('screen-result');
}

function retrySearch() {
  const overlay = document.getElementById('manual-overlay');
  overlay.style.display = 'flex';
}

function closeManual() {
  document.getElementById('manual-overlay').style.display = 'none';
}

async function submitManual() {
  const title = document.getElementById('manual-title').value.trim();
  const author = document.getElementById('manual-author').value.trim();
  if (!title) return;
  closeManual();
  showScreen('screen-loading');

  // 手动查询：构造一个假 OCR 结果直接跳到豆瓣查询
  try {
    const resp = await fetch(`${BACKEND_URL}/scan/manual`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, author })
    });
    const data = await resp.json();
    showResult(data);
  } catch (err) {
    showError('查询失败，请重试');
  }
}
</script>
</body>
</html>
```

- [ ] **Step 5: 提交前端**

```bash
git add frontend/
git commit -m "feat: add PWA frontend (manifest + HTML + CSS + JS)"
```

### 5D: 后端补充 /scan/manual 接口

- [ ] **Step 6: 在后端添加 /scan/manual 接口**（手动输入书名查询）

在 `backend/main.py` 末尾添加：

```python
class ManualRequest(BaseModel):
    title: str
    author: str = ""

@app.post("/scan/manual")
async def scan_manual(req: ManualRequest):
    loop = asyncio.get_event_loop()
    search_result = await loop.run_in_executor(None, search_book, req.title, req.author)

    if not search_result:
        return ScanResponse(
            title=req.title, author=req.author,
            score="", votes="", pub_year="",
            comments=[], douban_url="", confidence="high",
            douban_error="豆瓣未找到此书",
        )

    subject_id = search_result["subject_id"]
    detail = await loop.run_in_executor(None, get_book_detail, subject_id)

    return ScanResponse(
        title=search_result["title"],
        author=req.author,
        score=search_result["score"],
        votes=search_result["votes"],
        pub_year=detail.get("pub_year") or search_result["pub_year"],
        comments=detail.get("comments", []),
        douban_url=search_result["douban_url"],
        confidence="high",
    )
```

- [ ] **Step 7: 本地端到端验证**

用浏览器打开 `frontend/index.html`，注意：直接双击打开是 `file://` 协议，摄像头可能被限制。用 Python 起一个本地 server：

```bash
cd frontend
python3 -m http.server 3000
```

用手机访问 `http://你的Mac局域网IP:3000`（Mac 查 IP：`ifconfig | grep "inet " | grep -v 127`）

验收标准：
- 拍一张书封面 → 出现 loading → 出现结果页（有书名和评分）
- 点"结果不对？" → 弹出手动输入框 → 输入书名 → 查到结果
- 点"再拍一本" → 返回首屏

---

## Task 6: 部署到 Railway + Vercel

**Files:**
- Create: `backend/railway.json`（可选，Railway 自动检测 Procfile）

### 6A: 部署后端到 Railway

- [ ] **Step 1: 注册 Railway**

打开 railway.app → 用 GitHub 登录

- [ ] **Step 2: 新建项目**

Dashboard → New Project → Deploy from GitHub repo → 选择 book-scanner repo → 选择 `backend/` 目录（或 root，Railway 会自动找 Procfile）

> 如果 Railway 找不到 Procfile，在项目根目录加一个指向 backend 的配置：

```json
// railway.json（放在项目根目录）
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS",
    "buildCommand": "pip install -r backend/requirements.txt"
  },
  "deploy": {
    "startCommand": "cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT"
  }
}
```

- [ ] **Step 3: 设置环境变量**

Railway 项目 → Variables → 添加：
```
DASHSCOPE_API_KEY = sk-6396906889714bfbb54b7ea67c4e542e
```

- [ ] **Step 4: 验证部署成功**

```bash
curl https://你的railway地址.up.railway.app/health
```

Expected: `{"status":"ok"}`

### 6B: 部署前端到 Vercel

- [ ] **Step 5: 更新 BACKEND_URL**

把 `frontend/index.html` 中的：
```js
const BACKEND_URL = "http://localhost:8080";
```
改为 Railway 给的 URL：
```js
const BACKEND_URL = "https://你的railway地址.up.railway.app";
```

- [ ] **Step 6: 部署到 Vercel**

```bash
# 安装 vercel CLI（如果没有）
npm i -g vercel

cd frontend
vercel --prod
```

按提示操作，选择 `frontend/` 目录，framework 选 "Other"。

- [ ] **Step 7: 手机验证完整流程**

用手机 Safari 打开 Vercel 给的 URL：
- 拍封面 → 出结果（10秒内）
- 在 Safari 点"分享" → "添加到主屏幕" → 图标出现在桌面

- [ ] **Step 8: 最终提交**

```bash
git add railway.json frontend/index.html
git commit -m "deploy: configure Railway + Vercel deployment"
```

---

## 验收清单（全部通过才算 Phase 1 完成）

- [ ] `pytest tests/` 全部通过
- [ ] 本地 `/scan` 接口：《时间的秩序》能返回评分 8.9
- [ ] 本地 `/scan` 接口：《王安石传》能返回评分
- [ ] 手机访问 Vercel URL，拍封面能出结果
- [ ] Railway `/health` 返回 ok
- [ ] 出版年份超过10年显示 ⚠️ 橙色警告
- [ ] 豆瓣找不到书时，显示错误提示而不是崩溃
- [ ] 手动输入书名功能可用

---

## 已知限制（Phase 2 解决）

- 豆瓣反爬：小规模使用没问题，高频调用可能被临时封 IP
- 短评数量：详情页通常只有 4-6 条，不是完整的热门短评列表
- 无 Notion 回流（Phase 2 建新数据库后接入）
- 无历史记录页面
