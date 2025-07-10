# proxy_tool/writer/writer.py

import os
import yaml
import json
import logging
from typing import List, Dict, Any

from .. import config

def _ensure_output_dir_exists():
    """Ensures the output directory exists."""
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)

def write_proxies_to_plain_text(proxies: List[Dict[str, Any]]):
    """
    Writes a list of validated proxies to a plain text file.
    Each line contains the original proxy string.
    """
    _ensure_output_dir_exists()
    output_path = os.path.join(config.OUTPUT_DIR, config.PLAIN_TEXT_OUTPUT_FILENAME)
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            for proxy in proxies:
                # Assuming 'proxy_str' holds the original raw proxy string
                if 'proxy_str' in proxy:
                    f.write(proxy['proxy_str'] + '\n')
                else:
                    logging.warning(f"Skipping proxy without 'proxy_str' for plain text output: {proxy.get('ps', 'Unknown Proxy')}")
        logging.info(f"成功将 {len(proxies)} 个代理写入明文文件: {output_path}")
    except IOError as e:
        logging.error(f"写入明文文件失败: {e}")

def _convert_to_clash_format(proxy: Dict[str, Any]) -> Dict[str, Any]:
    """Converts a single proxy dictionary to Clash proxy format."""
    # Attempt to use the original proxy_str if available,
    # otherwise, try to construct a basic proxy.
    if 'proxy_str' in proxy and proxy['proxy_str'].startswith(('ss://', 'vmess://', 'trojan://', 'vless://', 'hy2://', 'tuic://')):
        # For protocols that Clash can import directly from their raw string
        # Note: This is a simplification. Real Clash conversion might need more parsing logic.
        # For vmess/trojan/vless, Clash generally expects a specific YAML structure,
        # but some tools can interpret the raw link.
        # Here we attempt to parse simple SS/VMess/Trojan links.
        # A full parser for each protocol to generate Clash YAML is more complex.
        # Let's assume proxy['parsed_data'] contains the necessary info for direct YAML mapping.
        # This part requires your proxy parser to output Clash-compatible fields.
        
        # Example for SS:
        if proxy['proxy_str'].startswith('ss://'):
            try:
                # Basic SS link parsing for Clash
                from urllib.parse import urlparse, unquote
                parsed_url = urlparse(proxy['proxy_str'])
                method_password, server_port = parsed_url.netloc.split('@')
                method, password = method_password.split(':')
                server, port = server_port.split(':')
                name = unquote(parsed_url.fragment) if parsed_url.fragment else f"Shadowsocks-{server}:{port}"
                return {
                    'name': name,
                    'type': 'ss',
                    'server': server,
                    'port': int(port),
                    'cipher': method,
                    'password': password
                }
            except Exception as e:
                logging.warning(f"无法将 SS 代理转换为 Clash 格式: {proxy['proxy_str']} - {e}")
                return None
        # For other protocols (VMess, Trojan, VLESS, Hy2, Tuic), they generally need
        # more sophisticated parsing to fit Clash's YAML structure.
        # The current 'proxy' dict should ideally already contain parsed fields.
        
        # Fallback: if the proxy object already has Clash-ready fields from parsing
        if proxy.get('type') and proxy.get('server') and proxy.get('port'):
            clash_proxy = {
                'name': proxy.get('ps', f"{proxy['type']}-{proxy['server']}:{proxy['port']}"),
                'type': proxy['type'],
                'server': proxy['server'],
                'port': proxy['port'],
            }
            if 'uuid' in proxy: clash_proxy['uuid'] = proxy['uuid']
            if 'alterId' in proxy: clash_proxy['alterId'] = proxy['alterId']
            if 'cipher' in proxy: clash_proxy['cipher'] = proxy['cipher']
            if 'password' in proxy: clash_proxy['password'] = proxy['password']
            if 'tls' in proxy: clash_proxy['tls'] = proxy['tls']
            if 'network' in proxy: clash_proxy['network'] = proxy['network']
            if 'ws-path' in proxy: clash_proxy['ws-path'] = proxy['ws-path']
            if 'ws-headers' in proxy: clash_proxy['ws-headers'] = proxy['ws-headers']
            if 'flow' in proxy: clash_proxy['flow'] = proxy['flow']
            if 'servername' in proxy: clash_proxy['servername'] = proxy['servername'] # for SNI
            # Add other common Clash fields as needed based on your proxy types
            return clash_proxy
    
    return None # Return None if conversion fails or unsupported format

def write_proxies_to_clash_yaml(proxies: List[Dict[str, Any]]):
    """
    Writes a list of validated proxies to a Clash YAML configuration file.
    """
    _ensure_output_dir_exists()
    output_path = os.path.join(config.OUTPUT_DIR, config.CLASH_OUTPUT_FILENAME)

    clash_proxies = []
    for proxy in proxies:
        clash_format = _convert_to_clash_format(proxy)
        if clash_format:
            clash_proxies.append(clash_format)
        else:
            logging.warning(f"无法将代理转换为 Clash 格式，跳过: {proxy.get('ps', 'Unknown Proxy')}")

    # Basic Clash configuration structure
    clash_config = {
        'proxies': clash_proxies,
        'proxy-groups': [
            {
                'name': 'Proxy',
                'type': 'select',
                'proxies': ['DIRECT'] + [p['name'] for p in clash_proxies if 'name' in p]
            },
            # Add more proxy groups or rules here as needed
        ],
        'rules': [
            'MATCH,Proxy' # Default rule to use the 'Proxy' group
        ]
    }

    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(clash_config, f, allow_unicode=True, sort_keys=False)
        logging.info(f"成功将 {len(clash_proxies)} 个代理写入 Clash YAML 文件: {output_path}")
    except IOError as e:
        logging.error(f"写入 Clash YAML 文件失败: {e}")
