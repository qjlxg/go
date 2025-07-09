# scraper/fetcher.py

import requests
import logging
from typing import List, Optional, Tuple # <-- 确保这一行存在

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def fetch_url_content(url: str, timeout: int) -> Tuple[Optional[str], Optional[str]]:
    """
    Fetches content from a given URL.
    Returns a tuple of (content, original_url) if successful, None otherwise.
    """
    logging.info(f"正在从 {url} 抓取内容...")
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        logging.info(f"成功从 {url} 获取内容 (状态码: {response.status_code})")
        return response.text, url
    except requests.exceptions.Timeout:
        logging.warning(f"抓取 {url} 超时。")
        return None, url
    except requests.exceptions.RequestException as e:
        logging.warning(f"抓取 {url} 时发生请求错误: {e}")
        return None, url
    except Exception as e:
        logging.error(f"抓取 {url} 时发生意外错误: {e}")
        return None, url

def fetch_all_proxy_sources(proxy_sources: List[str], timeout: int) -> List[Tuple[str, str]]:
    """
    Fetches content from all specified proxy sources.
    Returns a list of (content, original_url) tuples for successfully fetched sources.
    """
    all_raw_contents = []
    for url in proxy_sources:
        content, original_url = fetch_url_content(url, timeout)
        if content:
            all_raw_contents.append((content, original_url))
    return all_raw_contents
