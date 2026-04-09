# backend/main.py
import asyncio, os, time, logging
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

@app.post("/scan/douban")
async def scan_douban(req: DoubanRequest):
    loop = asyncio.get_event_loop()
    t0 = time.time()
    search_result = await loop.run_in_executor(None, search_book, req.title, req.author)
    t1 = time.time()
    if not search_result:
        logging.info(f"[scan/douban] 未命中 {t1-t0:.2f}s")
        return {"score": "", "votes": "", "pub_year": "", "comments": [], "douban_url": "", "douban_error": "豆瓣未找到此书"}
    subject_id = search_result["subject_id"]
    detail = await loop.run_in_executor(None, get_book_detail, subject_id)
    t2 = time.time()
    logging.info(f"[scan/douban] 搜索{t1-t0:.2f}s 详情{t2-t1:.2f}s 总{t2-t0:.2f}s")
    pub_year = detail.get("pub_year") or search_result["pub_year"]
    return {
        "score": search_result["score"],
        "votes": search_result["votes"],
        "pub_year": pub_year,
        "comments": detail.get("comments", []),
        "douban_url": search_result["douban_url"],
        "douban_error": "",
    }

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
