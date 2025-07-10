# main.py

import os
import asyncio
import logging
from typing import List, Dict, Any

# 从项目结构中导入模块
# 注意：这里直接导入子目录下的模块，因为 main.py 在根目录
import config # 导入 config.py
from scraper.fetcher import fetch_all_proxy_sources # 从 scraper/fetcher.py 导入
from parser.parser import ProxyParser # 从 parser/parser.py 导入
from validator.validator import ProxyValidator # 从 validator/validator.py 导入
from output.writer import write_proxies_to_plain_text, write_proxies_to_clash_yaml # 从 output/writer.py 导入
from models.proxy_model import Proxy # 从 models/proxy_model.py 导入

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

async def main():
    """
    主异步函数，运行代理抓取、解析、验证和输出的工作流。
    """
    logging.info("程序开始运行...")

    # 初始化组件
    parser = ProxyParser()
    validator = ProxyValidator()
    # writer 不需要单独初始化，因为它的函数是独立的

    # --- 步骤 1: 从配置的源抓取原始代理内容 ---
    logging.info("正在抓取原始代理内容...")
    # fetch_all_proxy_sources 返回 (content, original_url) 的列表
    raw_contents = fetch_all_proxy_sources(config.PROXY_SOURCES, config.FETCH_TIMEOUT)
    if not raw_contents:
        logging.error("未能从任何来源抓取到内容。请检查 PROXY_SOURCES 和网络连接。")
        return

    # --- 步骤 2: 解析原始内容为 Proxy 对象 ---
    logging.info("正在解析原始代理内容...")
    all_proxies: List[Proxy] = []
    for content, source_url in raw_contents:
        # parse_raw_content 返回 Proxy 对象的列表
        parsed_from_source = parser.parse_raw_content(content, source_url)
        logging.info(f"从 {source_url} 解析到 {len(parsed_from_source)} 个代理。")
        all_proxies.extend(parsed_from_source)

    if not all_proxies:
        logging.warning("未解析到任何代理。请检查代理源内容和解析逻辑。")
        return

    logging.info(f"总共解析到 {len(all_proxies)} 个代理。")

    # --- 步骤 3: 代理去重 ---
    logging.info("正在进行代理去重...")
    deduplicated_proxies: List[Proxy] = []
    seen_keys = set()
    for proxy in all_proxies:
        key = proxy.generate_key() # 调用 Proxy 对象的 generate_key 方法
        if key not in seen_keys:
            deduplicated_proxies.append(proxy)
            seen_keys.add(key)
    logging.info(f"去重后剩下 {len(deduplicated_proxies)} 个代理。")

    if not deduplicated_proxies:
        logging.warning("去重后没有剩余代理。")
        return

    # --- 步骤 4: 并发验证代理 ---
    logging.info(f"正在并发验证 {len(deduplicated_proxies)} 个代理...")
    # validate_proxies_concurrently 返回验证通过的 Proxy 对象列表
    validated_proxies = await validator.validate_proxies_concurrently(deduplicated_proxies)

    if not validated_proxies:
        logging.warning("没有代理通过验证。")
        return

    # --- 步骤 5: 按延迟排序有效代理 ---
    logging.info("正在按延迟排序有效代理...")
    # 确保只对有延迟（即通过验证）的代理进行排序
    sorted_proxies = sorted(
        [p for p in validated_proxies if p.latency is not None],
        key=lambda p: p.latency
    )
    logging.info(f"排序后，有 {len(sorted_proxies)} 个代理可供输出。")

    # --- 步骤 6: 如果配置了，选择前 N 个代理 ---
    output_proxies = sorted_proxies
    if config.TOP_N_PROXIES is not None and config.TOP_N_PROXIES > 0:
        output_proxies = sorted_proxies[:config.TOP_N_PROXIES]
        logging.info(f"已选择前 {len(output_proxies)} 个代理进行输出。")

    # --- 步骤 7: 写入输出文件 ---
    logging.info("正在写入输出文件...")
    
    # 转换为字典列表，以便 writer 模块处理
    output_proxies_dicts = [p.to_dict() for p in output_proxies]

    # 写入明文文件
    write_proxies_to_plain_text(output_proxies_dicts)

    # 写入 Clash YAML 文件
    write_proxies_to_clash_yaml(output_proxies_dicts)

    logging.info("输出文件生成完成。")
    logging.info("程序运行结束。")

if __name__ == "__main__":
    # 确保 output 目录在程序开始前就存在
    import os
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    asyncio.run(main())
