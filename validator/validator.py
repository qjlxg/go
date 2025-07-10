# proxy_tool/validator/validator.py

import asyncio
import aiohttp
import logging
from typing import List, Dict, Any, Optional

from .. import config

class ProxyValidator:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def _check_tcp_latency(self, server: str, port: int) -> Optional[float]:
        """Checks the TCP latency of a proxy."""
        try:
            conn_start_time = asyncio.get_event_loop().time()
            # Use open_connection for direct TCP check
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(server, port),
                timeout=config.PROXY_CHECK_TIMEOUT
            )
            conn_end_time = asyncio.get_event_loop().time()
            writer.close()
            await writer.wait_closed()
            latency_ms = (conn_end_time - conn_start_time) * 1000
            self.logger.debug(f"代理 {server}:{port} TCP 连接成功，延迟: {latency_ms:.2f}ms")
            return latency_ms
        except asyncio.TimeoutError:
            self.logger.debug(f"代理 {server}:{port} TCP 连接超时。")
            return None
        except Exception as e:
            self.logger.debug(f"代理 {server}:{port} TCP 连接失败: {e}")
            return None

    # 移除了 _get_ip_info 函数，因为我们不再需要它。
    # async def _get_ip_info(self, ip_address: str) -> Dict[str, Any]:
    #     """Fetches IP information from a public API."""
    #     url = config.IP_API_URL.format(ip=ip_address)
    #     try:
    #         async with aiohttp.ClientSession() as session:
    #             async with session.get(url, timeout=config.IP_API_FETCH_TIMEOUT) as response:
    #                 if response.status == 200:
    #                     data = await response.json()
    #                     if data and data.get('status') == 'success':
    #                         self.logger.debug(f"成功获取 IP {ip_address} 信息。")
    #                         return data
    #                     else:
    #                         self.logger.warning(f"IP 信息 API 返回不良状态或错误: {data.get('message', '未知错误')}.")
    #                         return {}
    #                 elif response.status == 429:
    #                     self.logger.warning(f"获取 IP 信息时发生 HTTP 客户端错误: {ip_address}, 错误: {response.status}, message='Too Many Requests', url='{url}'")
    #                     return {}
    #                 else:
    #                     self.logger.warning(f"获取 IP 信息时发生 HTTP 错误: {ip_address}, 状态码: {response.status}, URL: {url}")
    #                     return {}
    #     except asyncio.TimeoutError:
    #         self.logger.warning(f"获取 IP 信息超时: {ip_address}")
    #         return {}
    #     except aiohttp.ClientError as e:
    #         self.logger.warning(f"获取 IP 信息时发生 HTTP 客户端错误: {ip_address}, 错误: {e}")
    #         return {}
    #     except Exception as e:
    #         self.logger.error(f"获取 IP 信息时发生未知错误: {ip_address}, 错误: {e}")
    #         return {}

    async def validate_proxy(self, proxy: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Validates a single proxy by checking TCP latency.
        IP information lookup is removed.
        """
        proxy_type = proxy.get('type')
        server = proxy.get('server')
        port = proxy.get('port')
        ps = proxy.get('ps', f"{proxy_type}-{server}:{port}") # Proxy name/tag

        if not all([proxy_type, server, port]):
            self.logger.warning(f"跳过无效代理（信息不完整）: {proxy}")
            return None

        self.logger.debug(f"正在验证代理 {ps} ({server}:{port})...")

        # --- Step 1: Check TCP Latency ---
        latency = await self._check_tcp_latency(server, port)

        if latency is not None:
            proxy['delay'] = latency
            # --- IP Information Lookup (Removed) ---
            # 移除了对 _get_ip_info 的调用及其结果处理
            proxy['country'] = None # 显式设为 None，表示不再获取
            proxy['regionName'] = None # 显式设为 None
            proxy['isp'] = None # 显式设为 None
            
            self.logger.info(f"代理 {ps} 验证成功。延迟: {latency:.2f}ms, 地区: {proxy['country']}, ISP: {proxy['isp']}")
            return proxy
        else:
            self.logger.debug(f"代理 {ps} 验证失败。")
            return None

    async def validate_proxies_concurrently(self, proxies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validates a list of proxies concurrently."""
        validator_tasks = []
        for proxy in proxies:
            validator_tasks.append(self.validate_proxy(proxy))

        results = []
        # Create a semaphore to limit concurrent tasks
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENT_CHECKS)

        async def limited_validate(task):
            async with semaphore:
                return await task

        # Gather results from concurrent tasks
        # Use return_when=asyncio.ALL_COMPLETED to wait for all tasks
        # or asyncio.FIRST_EXCEPTION if you want to stop on first error
        for f in asyncio.as_completed([limited_validate(task) for task in validator_tasks]):
            result = await f
            if result:
                results.append(result)
        
        return results
