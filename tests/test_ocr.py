# tests/test_ocr.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import pytest
from ocr import extract_book_info

def test_returns_dict_with_required_keys():
    img_path = "/Users/getupyang/Documents/ai/coding/book-scanner/testpic/微信图片_20260408112019_93_1.jpg"
    result = extract_book_info(img_path)
    assert isinstance(result, dict)
    assert "title" in result
    assert "author" in result
    assert "confidence" in result

def test_recognizes_shijian_de_zhixu():
    img_path = "/Users/getupyang/Documents/ai/coding/book-scanner/testpic/微信图片_20260408112019_93_1.jpg"
    result = extract_book_info(img_path)
    assert "时间" in result["title"]

def test_recognizes_wanganshe_zhuan():
    img_path = "/Users/getupyang/Documents/ai/coding/book-scanner/testpic/微信图片_20260408112020_94_1.jpg"
    result = extract_book_info(img_path)
    assert "王安石" in result["title"]

def test_handles_missing_file():
    result = extract_book_info("/nonexistent/path.jpg")
    assert "error" in result
