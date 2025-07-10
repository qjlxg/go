# main.py

import os
import asyncio
import logging
from typing import List, Dict, Any

from import config
from scraper import scraper
from parser import parser
from validator import validator
from writer import writer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

async def main():
    logging.info("程序开始运行...")

    # --- Step 1: Scrape raw proxy content ---
    logging.info("正在抓取原始代理内容...")
    raw_contents = await scraper.fetch_all_sources(config.PROXY_SOURCES)

    # --- Step 2: Parse raw content into proxy dictionaries ---
    logging.info("正在解析原始代理内容...")
    all_proxies = []
    for url, content in raw_contents.items():
        if content:
            parsed = parser.parse_content(content, url)
            logging.info(f"从 {url} 解析到 {len(parsed)} 个代理。")
            all_proxies.extend(parsed)
        else:
            logging.warning(f"无法从 {url} 获取内容，跳过解析。")

    logging.info(f"总共解析到 {len(all_proxies)} 个代理。")

    # --- Step 3: Deduplicate proxies ---
    logging.info("正在进行代理去重...")
    deduplicated_proxies = parser.deduplicate_proxies(all_proxies)
    logging.info(f"去重后剩下 {len(deduplicated_proxies)} 个代理。")

    # --- Step 4: Validate proxies concurrently ---
    logging.info(f"正在并发验证 {len(deduplicated_proxies)} 个代理...")
    validated_proxies = await validator.validate_proxies_concurrently(deduplicated_proxies)
    logging.info(f"完成并发验证。发现 {len(validated_proxies)} 个有效代理。")

    # --- Step 5: Sort validated proxies by latency ---
    logging.info("正在按延迟排序有效代理...")
    sorted_proxies = sorted(validated_proxies, key=lambda p: p.get('delay', float('inf')))
    logging.info(f"排序后，有 {len(sorted_proxies)} 个代理可供输出。")

    # --- Step 6: Select top N proxies if configured ---
    output_proxies = sorted_proxies
    if config.TOP_N_PROXIES is not None and config.TOP_N_PROXIES > 0:
        output_proxies = sorted_proxies[:config.TOP_N_PROXIES]
        logging.info(f"已选择前 {len(output_proxies)} 个代理进行输出。")

    # --- Step 7: Write output files ---
    logging.info("正在写入输出文件...")
    
    # 写入明文文件
    writer.write_proxies_to_plain_text(output_proxies)

    # 写入 Clash YAML 文件
    writer.write_proxies_to_clash_yaml(output_proxies)

    logging.info("输出文件生成完成。")
    logging.info("程序运行结束。")

if __name__ == "__main__":
    asyncio.run(main())
