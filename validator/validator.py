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
            writer.close() # 关闭写入器
            await writer.wait_closed() # 等待写入器关闭
            conn_end_time = asyncio.get_event_loop().time() # 记录连接结束时间
            latency_ms = (conn_end_time - conn_start_time) * 1000 # 计算延迟（毫秒）
            self.logger.debug(f"代理 {server}:{port} TCP 连接成功，延迟: {latency_ms:.2f}ms")
            return latency_ms
        except asyncio.TimeoutError:
            self.logger.debug(f"代理 {server}:{port} TCP 连接超时。")
            return None
        except Exception as e:
            self.logger.debug(f"代理 {server}:{port} TCP 连接失败: {e}")
            return None

    async def _check_http_access(self, proxy: Proxy) -> bool:
        """
        异步函数：检查代理是否能通过 HTTP/HTTPS 访问外部资源。
        Args:
            proxy (Proxy): Proxy 类的实例。
        Returns:
            bool: 如果代理能够访问测试 URL，返回 True；否则返回 False。
        """
        # 注意：aiohttp 的代理参数原生只支持 http:// 和 socks5:// 协议。
        # 对于 SS, Vmess, Trojan, Vless, Hy2, Tuic 等协议，aiohttp 无法直接使用。
        # 这意味着对于这些非标准协议的代理，此检查可能会失败，即使代理本身是有效的。
        # 如果需要支持，可能需要引入如 'aiohttp_socks' 这样的第三方库，或运行本地协议转换代理。

        # 尝试构建 aiohttp 可识别的代理 URL
        proxy_url = ""
        if proxy.type in ['http', 'https']:
            # 对于 HTTP/HTTPS 代理，直接构建 URL
            if proxy.username and proxy.password:
                proxy_url = f"http://{proxy.username}:{proxy.password}@{proxy.server}:{proxy.port}"
            else:
                proxy_url = f"http://{proxy.server}:{proxy.port}"
        elif proxy.type == 'socks5':
            # 对于 SOCKS5 代理，构建 URL (通常需要 aiohttp_socks)
            if proxy.username and proxy.password:
                proxy_url = f"socks5://{proxy.username}:{proxy.password}@{proxy.server}:{proxy.port}"
            else:
                proxy_url = f"socks5://{proxy.server}:{proxy.port}"
        else:
            # 对于其他协议类型，不构建 proxy_url，因为 aiohttp 不直接支持。
            # 这意味着这些类型的代理将跳过 HTTP 检查（或直接失败）。
            self.logger.debug(f"代理类型 {proxy.type} 不直接支持 aiohttp HTTP 访问检查。将跳过此检查。")
            return True # 默认返回 True，因为我们无法进行有效的 HTTP 检查，不应因此淘汰代理

        # 如果没有构建出有效的 proxy_url，也直接返回 True，表示无法进行 HTTP 检查
        if not proxy_url:
            return True

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    config.TEST_HTTP_URL,
                    proxy=proxy_url,
                    timeout=config.HTTP_CHECK_TIMEOUT,
                    allow_redirects=True # 允许重定向
                ) as response:
                    if response.status == 200:
                        self.logger.debug(f"代理 {proxy.ps} ({proxy.server}:{proxy.port}) HTTP/HTTPS 访问成功。")
                        return True
                    else:
                        self.logger.debug(f"代理 {proxy.ps} ({proxy.server}:{proxy.port}) HTTP/HTTPS 访问失败，状态码: {response.status}")
                        return False
        except asyncio.TimeoutError:
            self.logger.debug(f"代理 {proxy.ps} ({proxy.server}:{proxy.port}) HTTP/HTTPS 访问超时。")
            return False
        except aiohttp.ClientProxyConnectionError as e:
            self.logger.debug(f"代理 {proxy.ps} ({proxy.server}:{proxy.port}) HTTP/HTTPS 代理连接错误: {e}")
            return False
        except Exception as e:
            self.logger.debug(f"代理 {proxy.ps} ({proxy.server}:{proxy.port}) HTTP/HTTPS 访问失败: {e}")
            return False

    async def validate_proxy(self, proxy: Proxy) -> Optional[Proxy]:
        """
        异步函数：验证单个代理的连通性。
        Args:
            proxy (Proxy): Proxy 类的实例。
        Returns:
            Optional[Proxy]: 如果代理验证成功，返回包含延迟等信息的 Proxy 实例；否则返回 None。
        """
        proxy_type = proxy.type
        server = proxy.server
        port = proxy.port
        ps = proxy.ps

        if not all([proxy_type, server, port]):
            self.logger.warning(f"跳过无效代理（信息不完整）: {proxy.proxy_str}")
            return None

        self.logger.debug(f"正在验证代理 {ps} ({server}:{port})...")

        # --- 步骤 1: 检查 TCP 连通性并获取延迟 ---
        latency = await self._check_tcp_latency(server, port)

        if latency is None:
            self.logger.debug(f"代理 {ps} TCP 连通性检查失败。")
            return None

        proxy.delay = latency

        # --- 步骤 2: (可选) 检查 HTTP/HTTPS 可访问性 ---
        if config.ENABLE_HTTP_CHECK:
            http_access_ok = await self._check_http_access(proxy)
            if not http_access_ok:
                self.logger.debug(f"代理 {ps} HTTP/HTTPS 访问检查失败。")
                return None
            else:
                self.logger.debug(f"代理 {ps} HTTP/HTTPS 访问检查成功。")
        
        # IP 信息查询 (已移除)
        proxy.country = None 
        proxy.regionName = None 
        proxy.isp = None 
        
        self.logger.info(f"代理 {ps} 验证成功。延迟: {latency:.2f}ms")
        return proxy

    async def validate_proxies_concurrently(self, proxies: List[Proxy]) -> List[Proxy]:
        """
        异步函数：并发验证代理列表。
        Args:
            proxies (List[Proxy]): 包含 Proxy 实例的列表。
        Returns:
            List[Proxy]: 验证通过的 Proxy 实例列表。
        """
        validator_tasks = []
        for proxy in proxies:
            validator_tasks.append(self.validate_proxy(proxy))

        results = []
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENT_CHECKS)

        async def limited_validate(task):
            """带有并发限制的验证包装器。"""
            async with semaphore:
                return await task

        for f in asyncio.as_completed([limited_validate(task) for task in validator_tasks]):
            result = await f
            if result:
                results.append(result)
        
        self.logger.info(f"完成所有代理的并发验证。共发现 {len(results)} 个有效代理。")
        return results
