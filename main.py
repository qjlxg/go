# proxy_tool/main.py

import asyncio
import logging
from typing import List

# Import modules from our project structure
import config
from scraper.fetcher import fetch_all_proxy_sources
from parser.parser import ProxyParser
from validator.validator import ProxyValidator
from output.writer import ProxyWriter
from models.proxy_model import Proxy

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def main():
    """
    Main asynchronous function to run the proxy scraping, parsing, validation, and output workflow.
    """
    logging.info("程序开始运行...")

    # Initialize components
    parser = ProxyParser()
    validator = ProxyValidator()
    writer = ProxyWriter()

    # --- Step 1: Fetch raw proxy content from configured sources ---
    logging.info("正在抓取原始代理内容...")
    raw_contents = fetch_all_proxy_sources(config.PROXY_SOURCES, config.FETCH_TIMEOUT)
    if not raw_contents:
        logging.error("未能从任何来源抓取到内容。请检查 PROXY_SOURCES 和网络连接。")
        return

    # --- Step 2: Parse raw content into Proxy objects ---
    logging.info("正在解析原始代理内容...")
    all_proxies: List[Proxy] = []
    for content, source_url in raw_contents:
        parsed_from_source = parser.parse_raw_content(content, source_url)
        logging.info(f"从 {source_url} 解析到 {len(parsed_from_source)} 个代理。")
        all_proxies.extend(parsed_from_source)

    if not all_proxies:
        logging.warning("未解析到任何代理。请检查代理源内容和解析逻辑。")
        return

    logging.info(f"总共解析到 {len(all_proxies)} 个代理。")

    # --- Step 3: Deduplicate proxies ---
    logging.info("正在进行代理去重...")
    deduplicated_proxies: List[Proxy] = []
    seen_keys = set()
    for proxy in all_proxies:
        key = proxy.generate_key()
        if key not in seen_keys:
            deduplicated_proxies.append(proxy)
            seen_keys.add(key)
    logging.info(f"去重后剩下 {len(deduplicated_proxies)} 个代理。")

    if not deduplicated_proxies:
        logging.warning("去重后没有剩余代理。")
        return

    # --- Step 4: Validate proxies concurrently ---
    logging.info(f"正在并发验证 {len(deduplicated_proxies)} 个代理...")
    validated_proxies = await validator.validate_proxies_concurrently(deduplicated_proxies)

    if not validated_proxies:
        logging.warning("没有代理通过验证。")
        return

    # --- Step 5: Sort validated proxies by latency ---
    logging.info("正在按延迟排序有效代理...")
    # Filter out proxies without latency before sorting, although validate_proxy should set it.
    sorted_proxies = sorted(
        [p for p in validated_proxies if p.latency is not None],
        key=lambda p: p.latency
    )
    logging.info(f"排序后，有 {len(sorted_proxies)} 个代理可供输出。")

    # --- Step 6: Select top N proxies if configured ---
    output_proxies = sorted_proxies
    if config.TOP_N_PROXIES is not None and config.TOP_N_PROXIES > 0:
        output_proxies = sorted_proxies[:config.TOP_N_PROXIES]
        logging.info(f"已选择前 {len(output_proxies)} 个代理进行输出。")

    # --- Step 7: Write validated proxies to output files ---
    logging.info("正在写入输出文件...")
    writer.write_proxies_to_json(output_proxies)
    writer.write_proxies_to_clash_yaml(output_proxies)
    logging.info("输出文件生成完成。")

    logging.info("程序运行结束。")

if __name__ == "__main__":
    # Ensure the output directory exists before running
    import os
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    asyncio.run(main())
