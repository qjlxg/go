# scraper/fetcher.py

import asyncio
import aiohttp
import logging
from typing import List, Tuple, Optional

import config # 绝对导入 config 模块

# 获取当前模块的日志记录器
logger = logging.getLogger(__name__)

async def fetch_url(url: str, timeout: int) -> Optional[str]:
    """
    异步函数：从单个 URL 抓取内容。
    Args:
        url (str): 要抓取的 URL。
        timeout (int): 请求超时时间（秒）。
    Returns:
        Optional[str]: 如果成功抓取，返回网页内容字符串；否则返回 None。
    """
    try:
        # 使用 aiohttp.ClientSession 进行 HTTP 请求
        async with aiohttp.ClientSession() as session:
            # 发送 GET 请求，并设置超时
            async with session.get(url, timeout=timeout) as response:
                if response.status == 200: # 检查 HTTP 状态码是否为 200 (成功)
                    logger.debug(f"成功抓取: {url}")
                    return await response.text() # 返回响应文本内容
                else:
                    logger.warning(f"抓取 {url} 失败，状态码: {response.status}")
                    return None # 抓取失败返回 None
    except asyncio.TimeoutError:
        logger.warning(f"抓取 {url} 超时。")
        return None # 超时返回 None
    except aiohttp.ClientError as e:
        logger.warning(f"抓取 {url} 时发生客户端错误: {e}")
        return None # 客户端错误返回 None
    except Exception as e:
        logger.error(f"抓取 {url} 时发生未知错误: {e}")
        return None # 其他异常返回 None

async def fetch_all_proxy_sources(urls: List[str], timeout: int) -> List[Tuple[str, str]]:
    """
    异步函数：并发抓取所有代理源 URL 的内容。
    Args:
        urls (List[str]): 代理源 URL 列表。
        timeout (int): 每个请求的超时时间（秒）。
    Returns:
        List[Tuple[str, str]]: 包含 (内容, 原始URL) 元组的列表。
    """
    logger.info("开始并发抓取所有代理源。")
    tasks = []
    # 为每个 URL 创建一个抓取任务
    for url in urls:
        tasks.append(fetch_url(url, timeout))

    # 使用 asyncio.gather 并发运行所有任务
    # return_exceptions=True 确保即使有任务失败，其他任务也会继续完成
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    fetched_contents = []
    # 处理每个任务的结果
    for i, result in enumerate(results):
        url = urls[i]
        if isinstance(result, str): # 如果结果是字符串，表示抓取成功
            fetched_contents.append((result, url))
        else:
            # 如果结果是异常或 None，说明抓取失败，日志已在 fetch_url 中记录
            pass 
    
    logger.info(f"完成所有代理源抓取。成功抓取到 {len(fetched_contents)} 个源的内容。")
    return fetched_contents # 返回成功抓取的内容列表
