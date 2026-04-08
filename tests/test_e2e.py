# tests/test_e2e.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from ocr import extract_book_info
from douban import search_book, get_book_detail

def test_full_pipeline_shijian():
    img_path = "/Users/getupyang/Documents/ai/coding/book-scanner/testpic/微信图片_20260408112019_93_1.jpg"
    ocr = extract_book_info(img_path)
    assert "error" not in ocr, f"OCR 失败: {ocr}"
    assert "时间" in ocr["title"]
    douban = search_book(ocr["title"], ocr.get("author", ""))
    assert douban is not None, "豆瓣搜索失败"
    assert float(douban["score"]) > 8.0
    detail = get_book_detail(douban["subject_id"])
    assert len(detail["comments"]) >= 1
    assert detail["pub_year"] == "2019"

def test_full_pipeline_wanganshe():
    img_path = "/Users/getupyang/Documents/ai/coding/book-scanner/testpic/微信图片_20260408112020_94_1.jpg"
    ocr = extract_book_info(img_path)
    assert "error" not in ocr
    assert "王安石" in ocr["title"]
    douban = search_book(ocr["title"], ocr.get("author", ""))
    assert douban is not None
    assert float(douban["score"]) > 0
