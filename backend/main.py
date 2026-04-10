# backend/main.py
import asyncio, os, time, logging, re
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from ocr import extract_book_info_from_base64
from douban import search_book, get_book_detail

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Phase 2: 收紧为具体 Vercel 域名
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

class ManualRequest(BaseModel):
    title: str
    author: str = ""

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/scan", response_model=ScanResponse)
async def scan(req: ScanRequest):
    t0 = time.time()
    loop = asyncio.get_event_loop()

    ocr_result = await loop.run_in_executor(
        None, extract_book_info_from_base64, req.image, req.mime_type
    )
    t1 = time.time()
    logging.info(f"[scan] OCR: {t1-t0:.2f}s → {ocr_result.get('title','ERR')}")

    if "error" in ocr_result:
        raise HTTPException(status_code=422, detail=f"OCR失败: {ocr_result['error']}")
    title = ocr_result.get("title", "")
    author = ocr_result.get("author", "")
    confidence = ocr_result.get("confidence", "low")
    if not title:
        raise HTTPException(status_code=422, detail="无法识别书名，请重新拍摄")

    douban_error = ""
    score, votes, pub_year, comments, douban_url = "", "", "", [], ""
    search_result = await loop.run_in_executor(None, search_book, title, author)
    t2 = time.time()
    logging.info(f"[scan] 豆瓣搜索: {t2-t1:.2f}s → {search_result['subject_id'] if search_result else 'None'}")

    if search_result:
        subject_id = search_result["subject_id"]
        score = search_result["score"]
        votes = search_result["votes"]
        pub_year = search_result["pub_year"]
        douban_url = search_result["douban_url"]
        detail = await loop.run_in_executor(None, get_book_detail, subject_id)
        t3 = time.time()
        logging.info(f"[scan] 豆瓣详情: {t3-t2:.2f}s | 服务端总计: {t3-t0:.2f}s")
        comments = detail.get("comments", [])
        if not pub_year and detail.get("pub_year"):
            pub_year = detail["pub_year"]
    else:
        douban_error = "豆瓣未找到此书"
        logging.info(f"[scan] 豆瓣未命中 | 服务端总计: {t2-t0:.2f}s")

    return ScanResponse(
        title=title, author=author, score=score, votes=votes,
        pub_year=pub_year, comments=comments, douban_url=douban_url,
        confidence=confidence, douban_error=douban_error,
    )

class OcrOnlyResponse(BaseModel):
    title: str
    author: str
    confidence: str
    ocr_error: str = ""

class DoubanRequest(BaseModel):
    title: str
    author: str = ""

@app.post("/scan/ocr", response_model=OcrOnlyResponse)
async def scan_ocr(req: ScanRequest):
    loop = asyncio.get_event_loop()
    t0 = time.time()
    ocr_result = await loop.run_in_executor(
        None, extract_book_info_from_base64, req.image, req.mime_type
    )
    logging.info(f"[scan/ocr] {time.time()-t0:.2f}s → {ocr_result.get('title','ERR')}")
    if "error" in ocr_result:
        raise HTTPException(status_code=422, detail=f"OCR失败: {ocr_result['error']}")
    title = ocr_result.get("title", "")
    if not title:
        raise HTTPException(status_code=422, detail="无法识别书名，请重新拍摄")
    return OcrOnlyResponse(
        title=title,
        author=ocr_result.get("author", ""),
        confidence=ocr_result.get("confidence", "low"),
    )

def _clean_title(raw: str) -> str:
    """清洗OCR书名，去掉噪音，提高豆瓣搜索命中率"""
    # 去掉英文标题部分（连续英文大写单词）
    t = re.sub(r'\b[A-Z][A-Z\s]+[A-Z]\b', '', raw)
    # 去掉括号及其内容：(上)(下)(一) 等
    t = re.sub(r'[（(][上下一二三四五六七八九十\dⅠⅡⅢIVV]+[）)]', '', t)
    # 去掉"著/译/编"等后缀
    t = re.sub(r'[\s·]*[著译编]+$', '', t)
    return t.strip() or raw

def _clean_author(raw: str) -> str:
    """清洗OCR作者，去掉 [国籍]、著、译等"""
    a = re.sub(r'\[.*?\]', '', raw)
    a = re.sub(r'[\s]*[著译编][\s]*', ' ', a)
    return a.strip().split()[0] if a.strip() else raw

@app.post("/scan/douban")
async def scan_douban(req: DoubanRequest):
    loop = asyncio.get_event_loop()
    t0 = time.time()
    clean_title = _clean_title(req.title)
    clean_author = _clean_author(req.author)
    logging.info(f"[scan/douban] 清洗: '{req.title}' → '{clean_title}', '{req.author}' → '{clean_author}'")
    search_result = await loop.run_in_executor(None, search_book, clean_title, clean_author)
    t1 = time.time()
    logging.info(f"[scan/douban] 搜索{t1-t0:.2f}s → {search_result['subject_id'] if search_result else 'None'}")
    if not search_result:
        return {"score": "", "votes": "", "pub_year": "", "comments": [], "douban_url": "", "douban_error": "豆瓣未找到此书"}
    # 搜索结果先返回评分，同时异步拿短评不阻塞
    return {
        "score": search_result["score"],
        "votes": search_result["votes"],
        "pub_year": search_result["pub_year"],
        "subject_id": search_result["subject_id"],
        "comments": [],
        "douban_url": search_result["douban_url"],
        "douban_error": "",
    }

class CommentsRequest(BaseModel):
    subject_id: str

@app.post("/scan/comments")
async def scan_comments(req: CommentsRequest):
    loop = asyncio.get_event_loop()
    t0 = time.time()
    detail = await loop.run_in_executor(None, get_book_detail, req.subject_id)
    logging.info(f"[scan/comments] {time.time()-t0:.2f}s → {len(detail.get('comments',[]))}条")
    return {"comments": detail.get("comments", [])}

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
        title=search_result["title"], author=req.author,
        score=search_result["score"], votes=search_result["votes"],
        pub_year=detail.get("pub_year") or search_result["pub_year"],
        comments=detail.get("comments", []),
        douban_url=search_result["douban_url"],
        confidence="high",
    )
