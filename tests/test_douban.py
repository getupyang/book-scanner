# tests/test_douban.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import pytest
from douban import search_book, get_book_detail

def test_search_returns_score():
    result = search_book("时间的秩序", "卡洛·罗韦利")
    assert result is not None
    assert "score" in result
    assert float(result["score"]) > 0

def test_search_returns_votes():
    result = search_book("时间的秩序", "卡洛·罗韦利")
    assert "votes" in result
    assert int(result["votes"]) > 1000

def test_search_returns_subject_id():
    result = search_book("时间的秩序", "卡洛·罗韦利")
    assert "subject_id" in result
    assert result["subject_id"]

def test_get_detail_returns_pub_year():
    result = get_book_detail("33424487")  # 时间的秩序
    assert "pub_year" in result
    assert result["pub_year"] == "2019"

def test_get_detail_returns_comments():
    result = get_book_detail("33424487")
    assert "comments" in result
    assert len(result["comments"]) >= 1

def test_search_not_found_returns_none():
    result = search_book("xyzxyzxyz完全不存在的书名123456", "")
    assert result is None
