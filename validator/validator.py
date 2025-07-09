# validator/validator.py

import asyncio
import aiohttp # For asynchronous HTTP requests
import socket
import time
import logging
from typing import List, Optional, Dict, Any # <-- 确保这一行存在

from models.proxy_model import Proxy
import config # Import config for IP_API_URL and timeouts

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ProxyValidator:
    def __init__(self):
        self.ip_api_cache = {} # Cache for IP API responses to avoid redundant calls

    async def _check_tcp_latency(self, server: str, port: int, timeout: int) -> Optional[float]:
        """
        Asynchronously checks the TCP connection latency to a given server and port.
        Returns latency in milliseconds if successful, None otherwise.
        """
        try:
            start_time = time.time()
            # Use asyncio.open_connection for non-blocking connect
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(server, port), timeout=timeout
            )
            writer.close()
            await writer.wait_closed() # Ensure the writer is truly closed
            latency = (time.time() - start_time) * 1000 # Convert to milliseconds
            return round(latency, 2)
        except (asyncio.TimeoutError, ConnectionRefusedError, socket.gaierror, OSError) as e:
            logging.debug(f"TCP 拨号失败到 {server}:{port}: {e}")
            return None
        except Exception as e:
            logging.error(f"检查 {server}:{port} 延迟时发生意外错误: {e}")
            return None

    async def _get_ip_info(self, ip_address: str) -> Dict[str, Any]:
        """
        Asynchronously fetches IP information from an API.
        Caches results to prevent redundant API calls and respect rate limits.
        """
        if ip_address in self.ip_api_cache:
            return self.ip_api_cache[ip_address]

        url = config.IP_API_URL.format(ip=ip_address)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=config.FETCH_TIMEOUT) as response:
                    response.raise_for_status() # Raise an exception for bad status codes
                    data = await response.json()
                    if data and data.get("status") == "success":
                        info = {
                            "country": data.get("country"),
                            "countryCode": data.get("countryCode"),
                            "regionName": data.get("regionName"),
                            "city": data.get("city"),
                            "isp": data.get("isp"),
                        }
                        self.ip_api_cache[ip_address] = info
                        return info
                    else:
                        logging.warning(f"IP 信息 API 返回不良状态或错误: {data.get('message', '未知错误')}. URL: {url}")
                        return {"error": data.get("message", "未知错误")}
        except asyncio.TimeoutError:
            logging.warning(f"获取 IP 信息超时: {ip_address}")
            return {"error": "Timeout"}
        except aiohttp.ClientError as e:
            logging.warning(f"获取 IP 信息时发生 HTTP 客户端错误: {ip_address}, 错误: {e}")
            return {"error": str(e)}
        except Exception as e:
            logging.error(f"获取 IP 信息时发生意外错误: {ip_address}, 错误: {e}")
            return {"error": str(e)}

    async def validate_proxy(self, proxy: Proxy) -> Optional[Proxy]:
        """
        Asynchronously validates a single proxy by checking latency and fetching IP info.
        Returns the updated Proxy object if valid, None otherwise.
        """
        logging.debug(f"正在验证代理: {proxy.name} ({proxy.proxy_type} {proxy.server}:{proxy.port})")
        
        # Step 1: Check TCP latency
        latency = await self._check_tcp_latency(proxy.server, proxy.port, config.PROXY_CHECK_TIMEOUT)
        if latency is None:
            logging.debug(f"代理 {proxy.name} ({proxy.server}:{proxy.port}) 延迟检查失败或超时。")
            return None

        proxy.latency = latency
        proxy.last_checked = time.time() # Update last checked timestamp

        # Step 2: Get IP Information
        # Use the server's IP directly. For domain, it will be resolved by _get_ip_info
        ip_info = await self._get_ip_info(proxy.server)
        if ip_info and "error" not in ip_info:
            proxy.region = ip_info.get("country")
            proxy.isp = ip_info.get("isp")
        else:
            logging.debug(f"代理 {proxy.name} ({proxy.server}) IP 信息获取失败: {ip_info.get('error', '未知')}")
            # Do not return None here, proxy is still valid if only IP info failed
        
        logging.info(f"代理 {proxy.name} 验证成功。延迟: {proxy.latency}ms, 地区: {proxy.region}, ISP: {proxy.isp}")
        return proxy

    async def validate_proxies_concurrently(self, proxies: List[Proxy]) -> List[Proxy]:
        """
        Validates a list of proxies concurrently using asyncio.
        Returns a list of successfully validated proxies.
        """
        logging.info(f"开始并发验证 {len(proxies)} 个代理...")
        
        # Create a semaphore to limit concurrent tasks
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENT_CHECKS)
        
        async def bounded_validate(p: Proxy):
            async with semaphore:
                return await self.validate_proxy(p)

        tasks = [bounded_validate(p) for p in proxies]
        
        validated_proxies = []
        # Gather results, returning them in the order of the input tasks.
        # Setting return_when=asyncio.FIRST_EXCEPTION or similar could change behavior.
        # asyncio.gather will collect all results or raise the first exception.
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                # An exception occurred during validation of one proxy, log it.
                logging.error(f"并发验证中发生错误: {result}")
            elif result is not None:
                validated_proxies.append(result)
        
        logging.info(f"完成并发验证。发现 {len(validated_proxies)} 个有效代理。")
        return validated_proxies
