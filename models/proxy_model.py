# models/proxy_model.py

from typing import Dict, Any, Optional
import hashlib # 用于生成唯一哈希键
import json # 用于处理 JSON (如果需要)

import config # 绝对导入 config 模块

class Proxy:
    """
    代表一个验证通过的代理对象，包含其所有属性。
    """
    def __init__(self, proxy_str: str, ps: Optional[str] = None, ptype: Optional[str] = None,
                 server: Optional[str] = None, port: Optional[int] = None,
                 delay: Optional[float] = None, country: Optional[str] = None,
                 region_name: Optional[str] = None, isp: Optional[str] = None,
                 data: Optional[Dict[str, Any]] = None):
        """
        初始化 Proxy 对象。
        Args:
            proxy_str (str): 原始代理链接字符串 (如 ss://...)。
            ps (Optional[str]): 代理名称/标签。
            ptype (Optional[str]): 协议类型 (如 'ss', 'vmess', 'trojan')。
            server (Optional[str]): 服务器地址。
            port (Optional[int]): 服务器端口。
            delay (Optional[float]): 延迟（毫秒）。
            country (Optional[str]): IP 信息中的国家（已移除 IP 查询功能，此字段将为 None）。
            region_name (Optional[str]): IP 信息中的地区名称（已移除 IP 查询功能，此字段将为 None）。
            isp (Optional[str]): IP 信息中的 ISP（已移除 IP 查询功能，此字段将为 None）。
            data (Optional[Dict[str, Any]]): 用于存储所有额外的解析数据。
        """
        self.proxy_str = proxy_str  # 原始代理链接字符串
        self.ps = ps                # 代理名称
        self.type = ptype           # 协议类型
        self.server = server        # 服务器地址
        self.port = port            # 服务器端口
        self.delay = delay          # 延迟（毫秒）

        # IP 信息字段，由于已移除 IP 查询，这些字段将默认为 None
        self.country = country      
        self.regionName = region_name
        self.isp = isp              
        
        # 用于存储所有额外的解析数据，例如 VMess 的 UUID、alterId 等
        self.data = data if data is not None else {} 

        # 确保核心字段也在 data 字典中，方便 to_dict 和 generate_key 统一处理
        self.data['proxy_str'] = proxy_str
        if ps is not None: self.data['ps'] = ps
        if ptype is not None: self.data['type'] = ptype
        if server is not None: self.data['server'] = server
        if port is not None: self.data['port'] = port
        if delay is not None: self.data['delay'] = delay
        if country is not None: self.data['country'] = country
        if region_name is not None: self.data['regionName'] = region_name
        if isp is not None: self.data['isp'] = isp


    def generate_key(self) -> str:
        """
        为代理生成一个唯一的键，用于去重。
        Args:
            None
        Returns:
            str: 代理的唯一哈希键。
        """
        # 使用协议类型、服务器地址和端口作为基础唯一键
        key_parts = [self.type, self.server, str(self.port)]
        
        # 对于某些协议（如 VMess/VLESS），UUID 也是其唯一性的重要组成部分
        if self.type in ['vmess', 'vless'] and 'uuid' in self.data:
            key_parts.append(self.data['uuid'])
        
        # 对于 Trojan，如果密码是区分用户的（例如一个用户一个密码），则也应作为键的一部分
        if self.type == 'trojan' and 'password' in self.data and config.DEDUPLICATE_BY_PASSWORD_TROJAN: # 假设 config 里有一个控制此行为的变量
            key_parts.append(self.data['password'])

        # 对于 Hysteria2 和 TUIC，如果密码或 UUID 是区分节点的，也应考虑
        if self.type in ['hysteria2', 'tuic'] and 'password' in self.data:
             key_parts.append(self.data['password'])

        # 将所有关键部分用 ':' 连接起来，并进行 SHA256 哈希，生成一个紧凑且鲁棒的唯一键
        # filter(None, ...) 用于移除列表中的 None 值
        unique_string = ':'.join(filter(None, key_parts)) 
        return hashlib.sha256(unique_string.encode('utf-8')).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        """
        将 Proxy 对象转换为字典。
        Returns:
            Dict[str, Any]: 代理属性的字典表示。
        """
        # 返回存储在 self.data 中的所有解析出的数据
        return self.data

    def __repr__(self):
        """
        提供 Proxy 对象的字符串表示，方便调试。
        """
        return (f"Proxy(ps='{self.ps}', type='{self.type}', server='{self.server}', "
                f"port={self.port}, delay={self.delay:.2f}ms)")
