# proxy_tool/parser/parser.py

import base64
import json
import re
import urllib.parse
import logging
from typing import List, Optional, Dict, Any, Tuple

import yaml # For parsing Clash YAML
from models.proxy_model import Proxy # Import the Proxy model

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ProxyParser:
    def __init__(self):
        pass

    def parse_raw_content(self, raw_content: str, source_url: str) -> List[Proxy]:
        """
        Attempts to parse a raw string content (which could be a single link,
        multi-line links, or Clash YAML) into a list of Proxy objects.
        """
        raw_content = raw_content.strip()
        parsed_proxies = []

        # 1. Try parsing as Clash YAML first (most comprehensive)
        logging.debug(f"尝试将内容作为 Clash YAML 解析 (源: {source_url})")
        if "proxies:" in raw_content or "Proxy Group:" in raw_content or "Proxy Provider:" in raw_content:
            proxies_from_yaml = self._parse_clash_yaml(raw_content, source_url)
            if proxies_from_yaml:
                logging.info(f"成功从 Clash YAML 解析 {len(proxies_from_yaml)} 个代理 (源: {source_url})")
                parsed_proxies.extend(proxies_from_yaml)
                return parsed_proxies # If it's clearly a YAML, prioritize it and return.

        # 2. Try parsing as multi-line links (either plain or base64 encoded)
        logging.debug(f"尝试将内容作为多行链接解析 (源: {source_url})")
        lines = raw_content.splitlines()
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Try parsing as a single link directly
            proxy = self._parse_single_proxy_link(line, line)
            if proxy:
                parsed_proxies.append(proxy)
                continue

            # If direct parse fails, try base64 decoding the line and then parse
            try:
                decoded_line_bytes = base64.urlsafe_b64decode(self._pad_base64(line))
                decoded_line = decoded_line_bytes.decode('utf-8')
                proxy = self._parse_single_proxy_link(decoded_line, line)
                if proxy:
                    parsed_proxies.append(proxy)
                else:
                    logging.debug(f"无法解析 Base64 解码后的行: {decoded_line[:50]}... (原始: {line[:50]}...)")
            except Exception as e:
                logging.debug(f"行 Base64 解码失败或解析失败: {line[:50]}... 错误: {e}")

        # 3. If nothing found yet, try treating the whole content as one base64 blob
        if not parsed_proxies:
            logging.debug(f"尝试将整个内容作为 Base64 Blob 解析 (源: {source_url})")
            try:
                decoded_full_content_bytes = base64.urlsafe_b64decode(self._pad_base64(raw_content))
                decoded_full_content = decoded_full_content_bytes.decode('utf-8')
                # After decoding, it might be multi-line links or even a Clash YAML
                if "proxies:" in decoded_full_content or "Proxy Group:" in decoded_full_content:
                    proxies_from_yaml = self._parse_clash_yaml(decoded_full_content, source_url)
                    if proxies_from_yaml:
                        logging.info(f"成功从 Base64 解码后的 Clash YAML 解析 {len(proxies_from_yaml)} 个代理 (源: {source_url})")
                        parsed_proxies.extend(proxies_from_yaml)
                else:
                    # Treat as multi-line links after full content decode
                    decoded_lines = decoded_full_content.splitlines()
                    for line in decoded_lines:
                        line = line.strip()
                        if not line:
                            continue
                        proxy = self._parse_single_proxy_link(line, raw_content) # Use original raw_content as raw_link
                        if proxy:
                            parsed_proxies.append(proxy)
            except Exception as e:
                logging.debug(f"整个内容 Base64 解码或解析失败 (源: {source_url}) 错误: {e}")

        return parsed_proxies

    def _pad_base64(self, data: str) -> str:
        """Adds padding to a base64 string if necessary."""
        missing_padding = len(data) % 4
        if missing_padding != 0:
            data += '=' * (4 - missing_padding)
        return data

    def _parse_single_proxy_link(self, link: str, raw_link: str) -> Optional[Proxy]:
        """
        Parses a single proxy URI like vmess://, trojan://, ss://, http://, socks5://, etc.
        """
        link = link.strip()
        if not link:
            return None

        # Try to parse as a URL
        try:
            parsed_url = urllib.parse.urlparse(link)
            scheme = parsed_url.scheme.lower()
            
            # Default name from fragment or host
            name = urllib.parse.unquote(parsed_url.fragment) if parsed_url.fragment else parsed_url.netloc

            if scheme == "vmess":
                return self._parse_vmess(link, raw_link, name)
            elif scheme == "trojan":
                return self._parse_trojan(parsed_url, raw_link, name)
            elif scheme == "ss":
                return self._parse_ss(link, raw_link, name)
            elif scheme == "vless":
                return self._parse_vless(parsed_url, raw_link, name)
            elif scheme == "hysteria2":
                return self._parse_hysteria2(parsed_url, raw_link, name)
            elif scheme in ["http", "https", "socks5", "socks4"]:
                return self._parse_http_socks(parsed_url, raw_link, name)
            else:
                logging.debug(f"不支持的协议: {scheme} 在链接: {link[:50]}...")
                return None
        except Exception as e:
            logging.debug(f"解析单个链接失败: {link[:50]}... 错误: {e}")
            return None

    def _parse_vmess(self, link: str, raw_link: str, default_name: str) -> Optional[Proxy]:
        """Parses a vmess:// link."""
        # Vmess links usually have base64 encoded JSON after the scheme
        try:
            # Extract base64 part, typically everything after 'vmess://' and before '#'
            vmess_data_b64 = link[len("vmess://"):].split('#')[0]
            decoded_bytes = base64.urlsafe_b64decode(self._pad_base64(vmess_data_b64))
            vmess_config = json.loads(decoded_bytes.decode('utf-8'))

            name = default_name if default_name and default_name != vmess_config.get('add', '') else vmess_config.get('ps', default_name)
            if not name: name = f"vmess-{vmess_config.get('add', '')}:{vmess_config.get('port', '')}"

            proxy = Proxy(
                name=name,
                proxy_type="vmess",
                server=vmess_config.get('add', ''),
                port=int(vmess_config.get('port', 0)),
                uuid=vmess_config.get('id', ''),
                alter_id=int(vmess_config.get('aid', 0)),
                cipher=vmess_config.get('scy', vmess_config.get('method')), # 'scy' (security) is new, 'method' is old
                network=vmess_config.get('net', 'tcp'),
                tls=vmess_config.get('tls', '') == 'tls',
                skip_cert_verify=self._to_bool(vmess_config.get('verify_cert', False)), # Vmess specific cert verify
                host=vmess_config.get('host', ''),
                path=vmess_config.get('path', ''),
                service_name=vmess_config.get('servicename', ''), # For gRPC
                raw_link=raw_link
            )
            if not all([proxy.server, proxy.port, proxy.uuid]):
                raise ValueError("Vmess 链接缺少必要信息")
            return proxy
        except Exception as e:
            logging.debug(f"解析 Vmess 链接失败: {link[:50]}... 错误: {e}")
            return None

    def _parse_trojan(self, u: urllib.parse.ParseResult, raw_link: str, default_name: str) -> Optional[Proxy]:
        """Parses a trojan:// link."""
        try:
            password = u.username # For Trojan, username is password
            name = default_name if default_name else f"trojan-{u.hostname}:{u.port}"

            params = urllib.parse.parse_qs(u.query)
            proxy = Proxy(
                name=name,
                proxy_type="trojan",
                server=u.hostname,
                port=u.port,
                password=password,
                tls=True, # Trojan usually implies TLS
                skip_cert_verify=self._to_bool(params.get('allowInsecure', ['0'])[0] == '1' or params.get('skip-cert-verify', ['0'])[0] == '1'),
                network=params.get('type', [''])[0],
                host=params.get('sni', [u.hostname])[0], # SNI for Trojan
                path=params.get('path', [''])[0],
                service_name=params.get('serviceName', [''])[0],
                raw_link=raw_link
            )
            if not all([proxy.server, proxy.port, proxy.password]):
                raise ValueError("Trojan 链接缺少必要信息")
            return proxy
        except Exception as e:
            logging.debug(f"解析 Trojan 链接失败: {u.geturl()[:50]}... 错误: {e}")
            return None

    def _parse_ss(self, link: str, raw_link: str, default_name: str) -> Optional[Proxy]:
        """Parses an ss:// link."""
        try:
            # ss://method:password@server:port#name
            # The part before '@' is base64 encoded (method:password)
            match = re.match(r"ss:\/\/([^@]+)@([^:]+):(\d+)(?:#(.+))?", link)
            if not match:
                raise ValueError("SS 链接格式不匹配")

            encoded_cred = match.group(1)
            server = match.group(2)
            port = int(match.group(3))
            fragment_name = match.group(4)

            decoded_cred_bytes = base64.urlsafe_b64decode(self._pad_base64(encoded_cred))
            decoded_cred = decoded_cred_bytes.decode('utf-8')

            method, password = decoded_cred.split(':', 1)
            name = default_name if default_name else (fragment_name if fragment_name else f"ss-{server}:{port}")

            proxy = Proxy(
                name=name,
                proxy_type="ss",
                server=server,
                port=port,
                password=password,
                cipher=method,
                raw_link=raw_link
            )
            if not all([proxy.server, proxy.port, proxy.cipher, proxy.password]):
                raise ValueError("SS 链接缺少必要信息")
            return proxy
        except Exception as e:
            logging.debug(f"解析 SS 链接失败: {link[:50]}... 错误: {e}")
            return None

    def _parse_vless(self, u: urllib.parse.ParseResult, raw_link: str, default_name: str) -> Optional[Proxy]:
        """Parses a vless:// link."""
        try:
            uuid = u.username
            name = default_name if default_name else f"vless-{u.hostname}:{u.port}"

            params = urllib.parse.parse_qs(u.query)
            proxy = Proxy(
                name=name,
                proxy_type="vless",
                server=u.hostname,
                port=u.port,
                uuid=uuid,
                tls=self._to_bool(params.get('security', [''])[0] == 'tls'),
                skip_cert_verify=self._to_bool(params.get('allowInsecure', ['0'])[0] == '1' or params.get('skip-cert-verify', ['0'])[0] == '1'),
                network=params.get('type', [''])[0],
                host=params.get('host', [u.hostname])[0],
                path=params.get('path', [''])[0],
                service_name=params.get('serviceName', [''])[0], # For gRPC
                flow=params.get('flow', [''])[0],
                raw_link=raw_link
            )
            if not all([proxy.server, proxy.port, proxy.uuid]):
                raise ValueError("Vless 链接缺少必要信息")
            return proxy
        except Exception as e:
            logging.debug(f"解析 Vless 链接失败: {u.geturl()[:50]}... 错误: {e}")
            return None

    def _parse_hysteria2(self, u: urllib.parse.ParseResult, raw_link: str, default_name: str) -> Optional[Proxy]:
        """Parses a hysteria2:// link."""
        try:
            name = default_name if default_name else f"hysteria2-{u.hostname}:{u.port}"

            params = urllib.parse.parse_qs(u.query)
            proxy = Proxy(
                name=name,
                proxy_type="hysteria2",
                server=u.hostname,
                port=u.port,
                password=u.password, # Hysteria2 can have password in userinfo part
                obfs=params.get('obfs', [''])[0],
                obfs_password=params.get('obfsParam', [''])[0], # Hysteria2 obfs password
                tls=True, # Hysteria2 implies TLS
                skip_cert_verify=self._to_bool(params.get('insecure', ['0'])[0] == '1'),
                raw_link=raw_link
            )
            if not all([proxy.server, proxy.port]):
                raise ValueError("Hysteria2 链接缺少必要信息")
            return proxy
        except Exception as e:
            logging.debug(f"解析 Hysteria2 链接失败: {u.geturl()[:50]}... 错误: {e}")
            return None

    def _parse_http_socks(self, u: urllib.parse.ParseResult, raw_link: str, default_name: str) -> Optional[Proxy]:
        """Parses http(s):// or socks(4/5):// links."""
        try:
            proxy_type = u.scheme.lower()
            name = default_name if default_name else f"{proxy_type}-{u.hostname}:{u.port}"

            proxy = Proxy(
                name=name,
                proxy_type=proxy_type,
                server=u.hostname,
                port=u.port,
                password=u.password, # For basic auth
                tls=(proxy_type == 'https'), # HTTPS implies TLS
                raw_link=raw_link
            )
            if not all([proxy.server, proxy.port]):
                raise ValueError(f"{proxy_type} 链接缺少必要信息")
            return proxy
        except Exception as e:
            logging.debug(f"解析 {u.scheme} 链接失败: {u.geturl()[:50]}... 错误: {e}")
            return None

    def _parse_clash_yaml(self, content: str, source_url: str) -> List[Proxy]:
        """Parses a Clash YAML configuration content."""
        try:
            clash_config = yaml.safe_load(content)
            if not isinstance(clash_config, dict):
                logging.warning(f"Clash YAML 配置不是有效的字典 (源: {source_url})")
                return []

            proxies_raw = clash_config.get("proxies", [])
            if not isinstance(proxies_raw, list):
                logging.warning(f"Clash YAML 中 'proxies' 键不是列表 (源: {source_url})")
                return []

            parsed_proxies = []
            for p_dict in proxies_raw:
                if not isinstance(p_dict, dict):
                    logging.warning(f"Clash YAML 中发现非字典代理项: {p_dict}")
                    continue
                try:
                    proxy = self._clash_dict_to_proxy(p_dict, source_url)
                    if proxy:
                        parsed_proxies.append(proxy)
                except Exception as e:
                    logging.warning(f"解析 Clash YAML 单个代理失败: {p_dict.get('name', '未知')} 错误: {e}")
            return parsed_proxies
        except yaml.YAMLError as e:
            logging.debug(f"解析 Clash YAML 失败: {source_url} 错误: {e}")
            return []
        except Exception as e:
            logging.error(f"解析 Clash YAML 时发生意外错误: {source_url} 错误: {e}")
            return []

    def _clash_dict_to_proxy(self, p_dict: Dict[str, Any], source_url: str) -> Optional[Proxy]:
        """Converts a Clash proxy dictionary to a Proxy object."""
        proxy_type = p_dict.get("type", "").lower()
        name = p_dict.get("name", f"{proxy_type}-{p_dict.get('server', '')}:{p_dict.get('port', '')}")
        server = p_dict.get("server")
        port = p_dict.get("port")

        if not all([proxy_type, server, port]):
            logging.warning(f"Clash 代理缺少必要字段 (type, server, port): {p_dict}")
            return None

        proxy_args = {
            "name": name,
            "proxy_type": proxy_type,
            "server": server,
            "port": int(port),
            "raw_link": source_url # For Clash, the source URL is the "raw link"
        }

        if proxy_type == "vmess":
            proxy_args["uuid"] = p_dict.get("uuid")
            proxy_args["alter_id"] = p_dict.get("alterId")
            proxy_args["cipher"] = p_dict.get("cipher")
            proxy_args["network"] = p_dict.get("network")
            proxy_args["tls"] = self._to_bool(p_dict.get("tls"))
            proxy_args["skip_cert_verify"] = self._to_bool(p_dict.get("skip-cert-verify"))
            proxy_args["host"] = p_dict.get("ws-headers", {}).get("Host") or p_dict.get("host")
            proxy_args["path"] = p_dict.get("ws-path") or p_dict.get("path")
        elif proxy_type == "vless":
            proxy_args["uuid"] = p_dict.get("uuid")
            proxy_args["network"] = p_dict.get("network")
            proxy_args["tls"] = self._to_bool(p_dict.get("tls"))
            proxy_args["skip_cert_verify"] = self._to_bool(p_dict.get("skip-cert-verify"))
            proxy_args["host"] = p_dict.get("ws-headers", {}).get("Host") or p_dict.get("host")
            proxy_args["path"] = p_dict.get("ws-path") or p_dict.get("path")
            proxy_args["service_name"] = p_dict.get("grpc-service-name")
            proxy_args["flow"] = p_dict.get("flow")
        elif proxy_type == "trojan":
            proxy_args["password"] = p_dict.get("password")
            proxy_args["network"] = p_dict.get("network")
            proxy_args["tls"] = self._to_bool(p_dict.get("tls", True)) # Trojan usually TLS true
            proxy_args["skip_cert_verify"] = self._to_bool(p_dict.get("skip-cert-verify"))
            proxy_args["host"] = p_dict.get("sni") or p_dict.get("server") # SNI for Trojan
            proxy_args["path"] = p_dict.get("path")
            proxy_args["service_name"] = p_dict.get("serviceName")
        elif proxy_type == "ss":
            proxy_args["password"] = p_dict.get("password")
            proxy_args["cipher"] = p_dict.get("cipher")
        elif proxy_type == "hysteria2":
            proxy_args["password"] = p_dict.get("password")
            proxy_args["obfs"] = p_dict.get("obfs")
            proxy_args["obfs_password"] = p_dict.get("obfs-password")
            proxy_args["tls"] = True # Hysteria2 implies TLS
            proxy_args["skip_cert_verify"] = self._to_bool(p_dict.get("skip-cert-verify"))
        elif proxy_type in ["http", "https", "socks5", "socks4"]:
            proxy_args["password"] = p_dict.get("password")
            proxy_args["tls"] = (proxy_type == 'https') # HTTPS implies TLS
            proxy_args["host"] = p_dict.get("host") # For HTTP/SOCKS, host might be SNI

        return Proxy(**proxy_args)

    def _to_bool(self, value: Any) -> bool:
        """Converts various types to boolean, robustly handling strings like 'true', 'false', '1', '0'."""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lower_value = value.lower().strip()
            return lower_value in ("true", "1", "yes", "on", "tls")
        if isinstance(value, (int, float)):
            return value != 0
        return False # Default for None or other unexpected types
