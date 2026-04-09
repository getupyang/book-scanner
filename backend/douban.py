# backend/douban.py
import urllib.request, urllib.parse, re, time
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
    q = urllib.parse.quote(f"{title} {author}".strip())
    url = f"https://www.douban.com/search?cat=1001&q={q}"
    body = _fetch(url)
    if not body:
        return None

    section = body[body.find('search-result'):][:10000]

    id_match = re.search(r'sid:\s*(\d{6,})', section)
    if not id_match:
        id_match = re.search(r'subject%2F(\d{6,})%2F', section)
    if not id_match:
        return None
    subject_id = id_match.group(1)

    title_match = re.search(r'class="title"[^>]*>.*?<a[^>]+>([^<]+)</a>', section, re.DOTALL)
    found_title = title_match.group(1).strip() if title_match else title

    score_match = re.search(r'class="rating_nums">([\d.]+)</span>', section)
    score = score_match.group(1) if score_match else "0"

    votes_match = re.search(r'\((\d+)人评价\)', section)
    votes = votes_match.group(1) if votes_match else "0"

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

def get_book_detail(subject_id: str, delay: float = 0.1) -> dict:
    time.sleep(delay)
    url = f"https://book.douban.com/subject/{subject_id}/"
    body = _fetch(url)
    if not body:
        return {"pub_year": "", "comments": []}

    pub_year = ""
    year_match = re.search(r'出版年.*?(\d{4})', body)
    if year_match:
        pub_year = year_match.group(1)

    comments = re.findall(r'<span class="short">(.*?)</span>', body)
    comments = [c for c in comments if len(c) < 200]

    return {
        "pub_year": pub_year,
        "comments": comments[:5],
    }
