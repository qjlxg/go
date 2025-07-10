# validator/validator.py

import asyncio
import aiohttp
import logging
from typing import List, Dict, Any, Optional

import config # 绝对导入 config 模块
from models.proxy_model import Proxy # 导入 Proxy 类

# 获取当前模块的日志记录器
logger = logging.getLogger(__name__)

class ProxyValidator:
    def __init__(self):
        # 实例化时初始化日志记录器
        self.logger = logging.getLogger(__name__)

    async def _check_tcp_latency(self, server: str, port: int) -> Optional[float]:
        """
        异步函数：检查代理的 TCP 连通性并计算延迟。
        Args:
            server (str): 代理服务器地址。
            port (int): 代理服务器端口。
        Returns:
            Optional[float]: 如果 TCP 连接成功，返回延迟（毫秒）；否则返回 None。
        """
        try:
            conn_start_time = asyncio.get_event_loop().time() # 记录连接开始时间
            # 使用 asyncio.open_connection 进行直接的 TCP 连接检查
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(server, port),
                timeout=config.PROXY_CHECK_TIMEOUT # 设置连接超时时间
            )
            conn_end_time = asyncio.get_event_loop().time() # 记录连接结束时间
            writer.close() # 关闭写入器
            await writer.wait_closed() # 等待写入器关闭
            latency_ms = (conn_end_time - conn_start_time) * 1000 # 计算延迟（毫秒）
            self.logger.debug(f"代理 {server}:{port} TCP 连接成功，延迟: {latency_ms:.2f}ms")
            return latency_ms
        except asyncio.TimeoutError:
            self.logger.debug(f"代理 {server}:{port} TCP 连接超时。")
            return None
        except Exception as e:
            self.logger.debug(f"代理 {server}:{port} TCP 连接失败: {e}")
            return None

    async def validate_proxy(self, proxy: Proxy) -> Optional[Proxy]:
        """
        异步函数：验证单个代理的连通性。
        Args:
            proxy (Proxy): Proxy 类的实例。
        Returns:
            Optional[Proxy]: 如果代理验证成功，返回包含延迟等信息的 Proxy 实例；否则返回 None。
        """
        # 直接通过属性访问 Proxy 对象的数据
        proxy_type = proxy.type
        server = proxy.server
        port = proxy.port
        ps = proxy.ps # 直接获取代理名称

        if not all([proxy_type, server, port]): # 检查代理信息是否完整
            self.logger.warning(f"跳过无效代理（信息不完整）: {proxy.proxy_str}")
            return None

        self.logger.debug(f"正在验证代理 {ps} ({server}:{port})...")

        # --- 步骤 1: 检查 TCP 连通性并获取延迟 ---
        latency = await self._check_tcp_latency(server, port)

        if latency is not None: # 如果成功获取到延迟，说明代理有效
            proxy.delay = latency # 将延迟添加到 Proxy 对象中
            
            # --- IP 信息查询 (已移除) ---
            # 由于已决定不再进行 IP 信息查询，这里显式将相关字段设为 None
            proxy.country = None 
            proxy.regionName = None 
            proxy.isp = None 
            
            self.logger.info(f"代理 {ps} 验证成功。延迟: {latency:.2f}ms") # 不再打印地区和 ISP 信息
            return proxy
        else:
            self.logger.debug(f"代理 {ps} 验证失败。")
            return None

    async def validate_proxies_concurrently(self, proxies: List[Proxy]) -> List[Proxy]:
        """
        异步函数：并发验证代理列表。
        Args:
            proxies (List[Proxy]): 包含 Proxy 实例的列表。
        Returns:
            List[Proxy]: 验证通过的 Proxy 实例列表。
        """
        validator_tasks = []
        # 为每个 Proxy 实例创建一个验证任务
        for proxy in proxies:
            validator_tasks.append(self.validate_proxy(proxy))

        results = []
        # 创建一个信号量，用于限制并发任务的数量，避免同时检查过多代理
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENT_CHECKS)

        async def limited_validate(task):
            """带有并发限制的验证包装器。"""
            async with semaphore: # 进入信号量，当达到最大并发数时会等待
                return await task

        # 使用 asyncio.as_completed 收集任务结果，可以实时处理已完成的任务
        for f in asyncio.as_completed([limited_validate(task) for task in validator_tasks]):
            result = await f # 获取已完成任务的结果
            if result: # 如果结果不为 None，表示代理验证成功
                results.append(result)
        
        self.logger.info(f"完成所有代理的并发验证。共发现 {len(results)} 个有效代理。")
        return results
