from bs4 import BeautifulSoup
import requests
from ddgs import DDGS
from typing import List, Dict, Optional
import trafilatura
from urllib.parse import urlparse
import re

class SearchResult:
    def __init__(self, title: str, link: str, snippet: str, content: str = None):
        self.title = title
        self.link = link
        self.snippet = snippet
        self.content = content

def is_valid_url(url: str) -> bool:
    """Kiểm tra URL có hợp lệ không và loại bỏ một số domain không mong muốn"""
    blocked_domains = [
        'youtube.com', 'facebook.com', 'twitter.com', 'instagram.com',
        'tiktok.com', 'pinterest.com', 'reddit.com'
    ]
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        return (
            parsed.scheme in ('http', 'https') and
            len(parsed.netloc) > 0 and
            not any(bd in domain for bd in blocked_domains)
        )
    except:
        return False

def clean_text(text: str) -> str:
    """Làm sạch văn bản, loại bỏ khoảng trắng và ký tự đặc biệt dư thừa"""
    if not text:
        return ""
    # Loại bỏ các ký tự đặc biệt
    text = re.sub(r'[\n\r\t]+', ' ', text)
    # Loại bỏ khoảng trắng dư thừa
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def extract_main_content(url: str) -> Optional[str]:
    """Trích xuất nội dung chính từ trang web sử dụng trafilatura"""
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            # Sử dụng trafilatura để trích xuất nội dung chính
            content = trafilatura.extract(response.text)
            if content:
                return clean_text(content)

            # Fallback to BeautifulSoup nếu trafilatura không trích xuất được
            soup = BeautifulSoup(response.text, 'html.parser')

            # Loại bỏ các phần tử không cần thiết
            for element in soup(['script', 'style', 'nav', 'header', 'footer', 'iframe', 'aside']):
                element.decompose()

            # Thử các chiến lược khác nhau để lấy nội dung
            content_selectors = [
                'article', 'main', '[role="main"]', '.content', '#content',
                '.post', '.entry', '.article', '.post-content',
                '[itemprop="articleBody"]', '.markdown-body',  # GitHub content
                '.article__content', '.post__content',  # Blog formats
                '.documentation', '.docs-content',  # Documentation sites
                '#readme'  # GitHub README
            ]

            # 1. Thử tìm container chính
            for selector in content_selectors:
                main_content = soup.select_one(selector)
                if main_content:
                    cleaned_content = clean_text(main_content.get_text())
                    if len(cleaned_content) > 100:  # Kiểm tra độ dài tối thiểu
                        return cleaned_content

            # 2. Nếu không tìm được container chính, lấy tất cả đoạn văn có ý nghĩa
            paragraphs = []
            for p in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li']):
                text = clean_text(p.get_text())
                if len(text) > 20:  # Chỉ lấy đoạn văn có nghĩa
                    paragraphs.append(text)

            if paragraphs:
                return '\n'.join(paragraphs)
    except Exception as e:
        print(f"Error extracting content from {url}: {str(e)}")
        return None

def search_with_content(query: str, max_results: int = 5) -> List[SearchResult]:
    """Tìm kiếm với DuckDuckGo và trích xuất nội dung từ các kết quả"""
    results = []

    # Thêm từ khóa để tối ưu tìm kiếm tiếng Việt
    optimized_query = f'"{query}"' # Thêm dấu ngoặc kép để tìm chính xác cụm từ

    try:
        with DDGS() as ddgs:
            search_results = ddgs.text(optimized_query, max_results=max_results * 2)  # Lấy nhiều hơn để dự phòng

            # Convert generator to list để dễ debug
            search_results = list(search_results)
            print(f"Search results: {search_results}")  # Debug log

            for r in search_results:
                if len(results) >= max_results:
                    break

                print(f"Processing result: {r}")  # Debug log

                # Kiểm tra cả href và link
                url = r.get('href') or r.get('link')
                if not url:
                    print(f"Warning: URL not found in result: {r}")
                    continue

                if not is_valid_url(url):
                    continue

                try:
                    # Trích xuất nội dung
                    content = extract_main_content(url)
                    if not content:
                        continue

                    results.append(SearchResult(
                        title=r.get('title', ''),
                        link=url,  # Sử dụng url đã được xác định ở trên
                        snippet=r.get('body', ''),
                        content=content
                    ))
                except Exception as e:
                    print(f"Error processing result {url}: {str(e)}")
                    continue
    except Exception as e:
        print(f"Error during search: {str(e)}")

    return results[:max_results]

# Function để sử dụng service
def search_service(query: str, max_results: int = 5) -> List[Dict]:
    """
    Service function để tìm kiếm và trả về kết quả

    Args:
        query: Chuỗi tìm kiếm
        max_results: Số lượng kết quả tối đa

    Returns:
        List of dictionaries containing search results
    """
    results = search_with_content(query, max_results)
    # Đảm bảo kết quả trả về có cả link và href trỏ đến cùng URL
    formatted_results = []
    for r in results:
        formatted_results.append({
            "title": r.title,
            "link": r.link,
            "href": r.link,  # Thêm href trỏ đến cùng URL
            "snippet": r.snippet,
            "content": r.content
        })
    return formatted_results
