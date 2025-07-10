# parser/parser.py

import base64
import re
import yaml
import json # 导入 json 模块，用于处理 VMess/Hysteria2/TUIC 的 JSON 内容
import logging
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse, unquote

import config # 绝对导入 config 模块
from models.proxy_model import Proxy # 绝对导入 Proxy 模型

# 获取当前模块的日志记录器
logger = logging.getLogger(__name__)

class ProxyParser:
    def __init__(self):
        # 实例化时初始化日志记录器
        self.logger = logging.getLogger(__name__)

    def _parse_ss(self, link: str) -> Optional[Dict[str, Any]]:
        """
        解析 Shadowsocks (SS) 代理链接。
        """
        try:
            parsed_url = urlparse(link)
            if parsed_url.scheme != 'ss':
                return None # 不是 SS 链接，返回 None

            netloc_b64 = parsed_url.netloc
            creds = ""
            server_info = ""

            # SS 链接可能包含 base64 编码的凭据部分
            if '@' in netloc_b64:
                creds_b64, server_info = netloc_b64.split('@', 1)
                try:
                    # Python 的 base64.urlsafe_b64decode 需要正确的填充
                    # 尝试添加填充并解码
                    creds = base64.urlsafe_b64decode(creds_b64 + '==').decode('utf-8')
                except Exception:
                    # 如果 urlsafe 解码失败，尝试标准 base64 解码并处理 URL 字符
                    creds = base64.b64decode(creds_b64.replace('-', '+').replace('_', '/') + '==').decode('utf-8')
            else:
                # 没有凭据，只有服务器信息 (通常不完整或不符合标准)
                server_info = netloc_b64

            server, port = server_info.split(':', 1)
            port, *other_params = port.split('#', 1) # 分割端口和片段 (如 #name)
            
            method, password = creds.split(':', 1) if ':' in creds else (creds, '') # 分割加密方法和密码

            # 从 URL 片段中获取代理名称，如果没有则生成一个默认名称
            name = unquote(parsed_url.fragment) if parsed_url.fragment else f"Shadowsocks-{server}:{port}"

            return {
                'ps': name, # 代理名称
                'type': 'ss', # 协议类型
                'server': server,
                'port': int(port),
                'cipher': method, # 加密方法
                'password': password,
                'proxy_str': link # 原始代理链接字符串
            }
        except Exception as e:
            self.logger.debug(f"解析 SS 代理失败: {link} - 错误: {e}")
            return None

    def _parse_vmess(self, link: str) -> Optional[Dict[str, Any]]:
        """
        解析 VMess 代理链接。
        """
        try:
            if not link.startswith('vmess://'):
                return None # 不是 VMess 链接

            # 移除 'vmess://' 前缀并进行 base64 解码
            encoded_str = link[len('vmess://'):]
            decoded_str = base64.b64decode(encoded_str + '==').decode('utf-8') # 确保填充后解码
            data = json.loads(decoded_str) # 解码后的内容是 JSON 格式

            # 将解析出的数据映射到通用的代理信息字段
            proxy_info = {
                'ps': data.get('ps', f"VMess-{data.get('add')}:{data.get('port')}"), # 代理名称
                'type': 'vmess',
                'server': data.get('add'), # 服务器地址
                'port': int(data.get('port')), # 端口
                'uuid': data.get('id'), # 用户 ID (UUID)
                'alterId': int(data.get('aid', 0)), # 额外 ID
                'cipher': 'auto', # VMess 通常使用自动加密
                'network': data.get('net', 'tcp'), # 传输协议 (如 tcp, ws, grpc)
                'tls': data.get('tls', '') == 'tls', # 是否启用 TLS
                'proxy_str': link # 原始代理链接字符串
            }
            # 添加特定的网络设置（如 WebSocket、gRPC）
            if proxy_info['network'] == 'ws':
                proxy_info['ws-path'] = data.get('path', '/') # WebSocket 路径
                proxy_info['ws-headers'] = {'Host': data.get('host', data.get('add'))} # WebSocket 头部
            elif proxy_info['network'] == 'grpc':
                proxy_info['grpc-serviceName'] = data.get('path', '') # gRPC 服务名
            
            return proxy_info
        except Exception as e:
            self.logger.debug(f"解析 VMess 代理失败: {link} - 错误: {e}")
            return None

    def _parse_trojan(self, link: str) -> Optional[Dict[str, Any]]:
        """
        解析 Trojan 代理链接。
        """
        try:
            if not link.startswith('trojan://'):
                return None # 不是 Trojan 链接
            
            parsed_url = urlparse(link)
            password = parsed_url.username # 密码在用户名部分
            server = parsed_url.hostname # 服务器地址
            port = parsed_url.port # 端口
            # 从 URL 片段中获取代理名称
            name = unquote(parsed_url.fragment) if parsed_url.fragment else f"Trojan-{server}:{port}"

            proxy_info = {
                'ps': name, # 代理名称
                'type': 'trojan',
                'server': server,
                'port': int(port),
                'password': password,
                'tls': True, # Trojan 协议强制使用 TLS
                'proxy_str': link # 原始代理链接字符串
            }
            # 处理查询参数，如 SNI (服务器名称指示)
            query_params = dict(qp.split('=') for qp in parsed_url.query.split('&') if '=' in qp)
            if 'sni' in query_params:
                proxy_info['servername'] = query_params['sni']
            elif 'peer' in query_params: # 兼容一些旧版本或客户端的 peer 参数
                proxy_info['servername'] = query_params['peer']

            return proxy_info
        except Exception as e:
            self.logger.debug(f"解析 Trojan 代理失败: {link} - 错误: {e}")
            return None
    
    def _parse_vless(self, link: str) -> Optional[Dict[str, Any]]:
        """
        解析 VLESS 代理链接。
        """
        try:
            if not link.startswith('vless://'):
                return None # 不是 VLESS 链接
            
            # VLESS 链接通常包含 UUID@server:port，然后是查询参数和片段
            uuid_part, remaining_part = link[len('vless://'):].split('@', 1)
            server_info, *fragment_query = remaining_part.split('#', 1) # 先按 # 分割获取片段

            server_port_part, *query_params_part = server_info.split('?', 1) # 再按 ? 分割获取查询参数

            server, port = server_port_part.split(':', 1)

            # 解析查询参数
            query_params_dict = {}
            if query_params_part:
                for param in query_params_part[0].split('&'):
                    if '=' in param:
                        k, v = param.split('=', 1)
                        query_params_dict[k] = v

            # 从片段获取代理名称
            name = unquote(fragment_query[0]) if fragment_query else f"VLESS-{server}:{port}"

            proxy_info = {
                'ps': name, # 代理名称
                'type': 'vless',
                'server': server,
                'port': int(port),
                'uuid': uuid_part, # 用户 ID (UUID)
                'tls': query_params_dict.get('security', '') == 'tls', # 是否启用 TLS
                'network': query_params_dict.get('type', 'tcp'), # 传输协议
                'flow': query_params_dict.get('flow', ''), # 流控
                'proxy_str': link # 原始代理链接字符串
            }

            # 添加特定的网络设置（如 WebSocket、gRPC）
            if proxy_info['network'] == 'ws':
                proxy_info['ws-path'] = query_params_dict.get('path', '/')
                proxy_info['ws-headers'] = {'Host': query_params_dict.get('host', server)}
            elif proxy_info['network'] == 'grpc':
                proxy_info['grpc-serviceName'] = query_params_dict.get('serviceName', '')
                proxy_info['grpc-mode'] = query_params_dict.get('mode', 'gun') # stream 或 gun 模式

            # 添加 SNI (服务器名称指示)
            if 'sni' in query_params_dict:
                proxy_info['servername'] = query_params_dict['sni']
            elif 'host' in query_params_dict and proxy_info['network'] != 'ws':
                proxy_info['servername'] = query_params_dict['host']

            return proxy_info
        except Exception as e:
            self.logger.debug(f"解析 VLESS 代理失败: {link} - 错误: {e}")
            return None

    def _parse_hy2(self, link: str) -> Optional[Dict[str, Any]]:
        """
        解析 Hysteria2 (hy2) 代理链接。
        """
        try:
            if not link.startswith('hy2://'):
                return None # 不是 HY2 链接
            
            # 移除 'hy2://' 前缀
            encoded_str = link[len('hy2://'):]
            
            # 按 # 分割获取片段（代理名称）
            main_part, *fragment_part = encoded_str.split('#', 1)
            name = unquote(fragment_part[0]) if fragment_part else f"Hysteria2-Unknown"

            # 对主要部分进行 URL 安全的 Base64 解码
            decoded_main_part = base64.urlsafe_b64decode(main_part + '==').decode('utf-8')
            
            # Hysteria2 配置通常是 JSON 格式
            hy2_config = json.loads(decoded_main_part)

            proxy_info = {
                'ps': name, # 代理名称
                'type': 'hysteria2',
                'server': hy2_config.get('server'),
                'port': hy2_config.get('port'),
                'password': hy2_config.get('password'),
                'tls': True, # Hysteria2 协议强制使用 TLS
                'proxy_str': link # 原始代理链接字符串
            }
            # 添加 TLS 相关设置
            tls_settings = hy2_config.get('tls', {})
            if 'sni' in tls_settings:
                proxy_info['servername'] = tls_settings['sni']
            if 'insecure' in tls_settings:
                proxy_info['skip-cert-verify'] = tls_settings['insecure'] # 用于 Clash 的跳过证书验证

            return proxy_info

        except Exception as e:
            self.logger.debug(f"解析 Hysteria2 代理失败: {link} - 错误: {e}")
            return None

    def _parse_tuic(self, link: str) -> Optional[Dict[str, Any]]:
        """
        解析 TUIC 代理链接。
        """
        try:
            if not link.startswith('tuic://'):
                return None # 不是 TUIC 链接
            
            # 移除 'tuic://' 前缀
            main_part_with_frag = link[len('tuic://'):]
            
            # 按 # 分割获取片段（代理名称）
            main_part, *fragment_part = main_part_with_frag.split('#', 1)
            name = unquote(fragment_part[0]) if fragment_part else f"TUIC-Unknown"

            # 对主要部分进行 URL 安全的 Base64 解码
            decoded_main_part = base64.urlsafe_b64decode(main_part + '==').decode('utf-8')

            # TUIC 链接通常格式: password@server:port?params
            password_server_port, *query_part = decoded_main_part.split('?', 1)
            password, server_port = password_server_port.split('@', 1)
            server, port = server_port.split(':', 1)

            proxy_info = {
                'ps': name, # 代理名称
                'type': 'tuic',
                'server': server,
                'port': int(port),
                'password': password,
                'proxy_str': link # 原始代理链接字符串
            }

            # 解析查询参数
            if query_part:
                query_params = dict(qp.split('=') for qp in query_part[0].split('&') if '=' in qp)
                
                # 提取 TUIC 特有参数
                if 'version' in query_params: proxy_info['tuic_version'] = int(query_params['version'])
                if 'udp_relay_mode' in query_params: proxy_info['udp-relay-mode'] = query_params['udp_relay_mode']
                if 'disable_sni' in query_params: proxy_info['disable-sni'] = query_params['disable_sni'].lower() == '1'
                if 'congestion_controller' in query_params: proxy_info['congestion-controller'] = query_params['congestion_controller']
                if 'alpn' in query_params: proxy_info['alpn'] = query_params['alpn'].split(',') # ALPN 可以是逗号分隔列表
                
                # TLS 相关参数
                if 'sni' in query_params: proxy_info['servername'] = query_params['sni']
                if 'skip_cert_verify' in query_params: proxy_info['skip-cert-verify'] = query_params['skip_cert_verify'].lower() == '1' # 用于 Clash 的跳过证书验证

            return proxy_info

        except Exception as e:
            self.logger.debug(f"解析 TUIC 代理失败: {link} - 错误: {e}")
            return None

    def _parse_yaml_nodes(self, content: str) -> List[Proxy]:
        """
        解析 Clash-style YAML 内容，其中包含代理节点。
        """
        proxies: List[Proxy] = []
        try:
            data = yaml.safe_load(content)
            if isinstance(data, dict) and 'proxies' in data: # 检查 YAML 是否包含 'proxies' 键
                for p_data in data['proxies']:
                    proxy_type = p_data.get('type')
                    server = p_data.get('server')
                    port = p_data.get('port')
                    
                    if all([proxy_type, server, port]): # 确保代理信息完整
                        # 尝试根据解析到的 Clash 字典数据构建原始代理字符串
                        # 这部分逻辑需要根据您的 Clash 配置实际情况进行调整，以确保能正确反向构造出链接
                        proxy_str = ""
                        if proxy_type == 'ss':
                            cipher = p_data.get('cipher', 'auto')
                            password = p_data.get('password', '')
                            # 注意：SS 链接的 base64 编码部分是 method:password
                            encoded_creds = base64.urlsafe_b64encode(f'{cipher}:{password}'.encode()).decode().rstrip('=')
                            proxy_str = f"ss://{encoded_creds}@{server}:{port}#{p_data.get('name', 'SS')}"
                        elif proxy_type == 'vmess':
                            # VMess 通常是 base64(JSON)，这里尝试反向构造，可能不完全准确
                            # 更好的做法是如果原始链接存在则直接保留
                            try:
                                # 移除不必要的字段，只保留核心信息进行编码
                                temp_data = p_data.copy()
                                temp_data.pop('name', None)
                                temp_data['aid'] = temp_data.pop('alterId', 0) # Clash uses alterId
                                temp_data['add'] = temp_data.pop('server')
                                temp_data['port'] = str(temp_data.pop('port')) # Port must be string in VMess JSON
                                temp_data['id'] = temp_data.pop('uuid')
                                temp_data['net'] = temp_data.pop('network', 'tcp')
                                temp_data['path'] = temp_data.pop('ws-path', '/')
                                temp_data['host'] = temp_data.pop('ws-headers', {}).get('Host', temp_data['add'])
                                temp_data['tls'] = 'tls' if temp_data.get('tls') else ''
                                encoded_json = base64.b64encode(json.dumps(temp_data).encode()).decode().rstrip('=')
                                proxy_str = f"vmess://{encoded_json}"
                            except Exception as e:
                                self.logger.debug(f"无法从 VMess YAML 数据反向构造链接: {e}")
                                proxy_str = f"vmess://{server}:{port}" # 简单的 fallback
                        elif proxy_type == 'trojan':
                            password = p_data.get('password', '')
                            # 构建查询参数部分，如果存在 SNI
                            query_params = []
                            if 'servername' in p_data:
                                query_params.append(f"sni={p_data['servername']}")
                            query_string = f"?{'&'.join(query_params)}" if query_params else ""
                            proxy_str = f"trojan://{password}@{server}:{port}{query_string}#{p_data.get('name', 'Trojan')}"
                        elif proxy_type == 'vless':
                            uuid = p_data.get('uuid', '')
                            # 构建查询参数
                            query_params = []
                            if 'security' in p_data: query_params.append(f"security={p_data['security']}")
                            if 'network' in p_data: query_params.append(f"type={p_data['network']}")
                            if 'flow' in p_data: query_params.append(f"flow={p_data['flow']}")
                            if 'ws-path' in p_data: query_params.append(f"path={p_data['ws-path']}")
                            if 'ws-headers' in p_data and 'Host' in p_data['ws-headers']:
                                query_params.append(f"host={p_data['ws-headers']['Host']}")
                            if 'grpc-serviceName' in p_data: query_params.append(f"serviceName={p_data['grpc-serviceName']}")
                            if 'servername' in p_data: query_params.append(f"sni={p_data['servername']}")
                            query_string = f"?{'&'.join(query_params)}" if query_params else ""
                            proxy_str = f"vless://{uuid}@{server}:{port}{query_string}#{p_data.get('name', 'VLESS')}"
                        elif proxy_type == 'hysteria2':
                            # Hysteria2 YAML 转换为链接也需要重新编码 JSON
                            hy2_link_data = {'server': server, 'port': port, 'password': p_data.get('password')}
                            tls_settings = {}
                            if 'servername' in p_data: tls_settings['sni'] = p_data['servername']
                            if 'skip-cert-verify' in p_data: tls_settings['insecure'] = p_data['skip-cert-verify']
                            if tls_settings: hy2_link_data['tls'] = tls_settings
                            
                            encoded_hy2_json = base64.urlsafe_b64encode(json.dumps(hy2_link_data).encode()).decode().rstrip('=')
                            proxy_str = f"hy2://{encoded_hy2_json}#{p_data.get('name', 'Hysteria2')}"
                        elif proxy_type == 'tuic':
                            # TUIC YAML 转换为链接也需要重新编码
                            tuic_link_data = {'password': p_data.get('password')}
                            # 添加其他参数
                            query_params = []
                            if 'tuic_version' in p_data: query_params.append(f"version={p_data['tuic_version']}")
                            if 'udp-relay-mode' in p_data: query_params.append(f"udp_relay_mode={p_data['udp-relay-mode']}")
                            if 'disable-sni' in p_data: query_params.append(f"disable_sni={1 if p_data['disable-sni'] else 0}")
                            if 'congestion-controller' in p_data: query_params.append(f"congestion_controller={p_data['congestion-controller']}")
                            if 'alpn' in p_data and isinstance(p_data['alpn'], list): query_params.append(f"alpn={','.join(p_data['alpn'])}")
                            if 'servername' in p_data: query_params.append(f"sni={p_data['servername']}")
                            if 'skip-cert-verify' in p_data: query_params.append(f"skip_cert_verify={1 if p_data['skip-cert-verify'] else 0}")

                            query_string = f"?{'&'.join(query_params)}" if query_params else ""
                            encoded_main = base64.urlsafe_b64encode(f"{p_data.get('password')}@{server}:{port}{query_string}".encode()).decode().rstrip('=')
                            proxy_str = f"tuic://{encoded_main}#{p_data.get('name', 'TUIC')}"
                        else:
                            # 对于其他无法直接反向构造的协议，提供一个基本形式或警告
                            proxy_str = f"{proxy_type}://{server}:{port}#{p_data.get('name', 'Unknown')}" 
                            self.logger.warning(f"无法为协议类型 {proxy_type} 反向构造原始链接，使用通用格式。")

                        # 创建一个 Proxy 对象
                        proxy_obj = Proxy(
                            proxy_str=proxy_str, # 使用反向构造的链接
                            ps=p_data.get('name', f"{proxy_type}-{server}:{port}"),
                            ptype=proxy_type,
                            server=server,
                            port=port
                        )
                        # 将所有解析到的数据存储到 Proxy 对象的 data 属性中
                        proxy_obj.data.update(p_data)
                        proxies.append(proxy_obj)
                    else:
                        self.logger.warning(f"跳过不完整的 YAML 代理配置: {p_data}")
            else:
                self.logger.warning("YAML 内容不包含 'proxies' 键或格式不正确。")
        except yaml.YAMLError as e:
            self.logger.warning(f"解析 YAML 内容失败: {e}")
        except Exception as e:
            self.logger.error(f"解析 YAML 代理时发生未知错误: {e}")
        return proxies

    def parse_raw_content(self, content: str, source_url: str) -> List[Proxy]:
        """
        将从代理源抓取的原始内容解析为 Proxy 对象的列表。
        Args:
            content (str): 原始内容字符串。
            source_url (str): 代理来源 URL (用于日志记录)。
        Returns:
            List[Proxy]: 解析出的 Proxy 对象列表。
        """
        parsed_proxies: List[Proxy] = []

        # 尝试首先将内容作为 YAML (Clash 配置) 进行解析
        # 通常 YAML 配置会包含 "proxies:" 或 "proxy-groups:" 这样的关键字
        if "proxies:" in content or "proxy-groups:" in content:
            self.logger.debug(f"尝试将 {source_url} 内容解析为 YAML。")
            proxies_from_yaml = self._parse_yaml_nodes(content)
            if proxies_from_yaml:
                return proxies_from_yaml # 如果成功解析为 YAML，直接返回

        # 如果不是 YAML，则按行处理，尝试解析每行为代理链接
        lines = content.strip().split('\n')
        for line in lines:
            line = line.strip()
            if not line: # 跳过空行
                continue

            # 尝试 Base64 解码，如果看起来像 Base64 字符串
            # 匹配 Base64 字符集，并且长度是 4 的倍数
            if re.fullmatch(r'^[A-Za-z0-9+/=]+$', line) and len(line) % 4 == 0:
                try:
                    # Base64 解码
                    decoded_line = base64.b64decode(line).decode('utf-8').strip()
                    self.logger.debug(f"尝试将 {line[:20]}... (部分) 解码为 Base64。")
                    # 递归调用 parse_raw_content 处理解码后的内容
                    # 因为 Base64 解码后可能是一组新的链接列表
                    parsed_proxies.extend(self.parse_raw_content(decoded_line, f"decoded_from_{source_url}"))
                    continue # 处理完解码内容后，跳到原始内容的下一行
                except Exception as e:
                    self.logger.debug(f"Base64 解码 {line[:20]}... 失败: {e}。将尝试直接解析为链接。")
                    # 解码失败，说明不是有效的 Base64，继续尝试直接解析为链接

            # 尝试解析为各种代理链接类型
            proxy_data = None
            if line.startswith('ss://'):
                proxy_data = self._parse_ss(line)
            elif line.startswith('vmess://'):
                proxy_data = self._parse_vmess(line)
            elif line.startswith('trojan://'):
                proxy_data = self._parse_trojan(line)
            elif line.startswith('vless://'):
                proxy_data = self._parse_vless(line)
            elif line.startswith('hy2://'):
                proxy_data = self._parse_hy2(line)
            elif line.startswith('tuic://'):
                proxy_data = self._parse_tuic(line)
            # 如果有其他协议，可以在这里添加 elif 判断

            if proxy_data:
                # 从解析出的字典数据创建 Proxy 对象
                try:
                    proxy_obj = Proxy(
                        proxy_str=proxy_data.get('proxy_str', line), # 使用原始链接或解析到的链接
                        ps=proxy_data.get('ps'),
                        ptype=proxy_data.get('type'),
                        server=proxy_data.get('server'),
                        port=proxy_data.get('port')
                    )
                    # 将所有解析出的数据存储到 Proxy 对象的 data 属性中，方便后续处理
                    proxy_obj.data.update(proxy_data)
                    parsed_proxies.append(proxy_obj)
                except Exception as e:
                    self.logger.warning(f"创建 Proxy 对象失败 (可能缺少关键字段): {line} - 错误: {e}")
            else:
                self.logger.debug(f"未能解析行: {line[:50]}... (来自 {source_url})") # 记录未能解析的行

        return parsed_proxies

    def deduplicate_proxies(self, proxies: List[Proxy]) -> List[Proxy]:
        """
        根据代理的唯一键对 Proxy 对象列表进行去重。
        Args:
            proxies (List[Proxy]): 包含 Proxy 对象的列表。
        Returns:
            List[Proxy]: 去重后的 Proxy 对象列表。
        """
        seen_keys = set() # 用于存储已见过的代理的唯一键
        deduplicated = [] # 存储去重后的代理
        for proxy in proxies:
            key = proxy.generate_key() # 调用 Proxy 对象的 generate_key 方法生成唯一键
            if key not in seen_keys: # 如果键未出现过，则添加
                deduplicated.append(proxy)
                seen_keys.add(key)
        self.logger.info(f"去重前共有 {len(proxies)} 个代理，去重后剩下 {len(deduplicated)} 个。")
        return deduplicated
