# output/writer.py

import os
import yaml # 用于处理 YAML 格式（如 Clash 配置）
import json # 用于处理 JSON 格式
import logging
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse, unquote
import base64 # 用于 Base64 编码/解码

import config # 绝对导入 config 模块

# 获取当前模块的日志记录器
logger = logging.getLogger(__name__)

def _ensure_output_dir_exists():
    """确保输出目录存在，如果不存在则创建。"""
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)

def write_proxies_to_plain_text(proxies: List[Dict[str, Any]]):
    """
    将验证通过的代理列表写入明文文件。
    每行包含一个原始代理链接字符串。
    Args:
        proxies (List[Dict[str, Any]]): 包含代理信息的字典列表。
    """
    _ensure_output_dir_exists() # 确保输出目录存在
    output_path = os.path.join(config.OUTPUT_DIR, config.PLAIN_TEXT_OUTPUT_FILENAME)
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            for proxy in proxies:
                # 假设 'proxy_str' 包含了原始的代理链接字符串
                if 'proxy_str' in proxy:
                    f.write(proxy['proxy_str'] + '\n')
                else:
                    logger.warning(f"跳过没有 'proxy_str' 的代理，无法写入明文文件: {proxy.get('ps', '未知代理')}")
        logger.info(f"成功将 {len(proxies)} 个代理写入明文文件: {output_path}")
    except IOError as e:
        logger.error(f"写入明文文件失败: {e}")

def _convert_to_clash_format(proxy: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    将单个代理字典转换为 Clash 代理节点的字典格式。
    Args:
        proxy (Dict[str, Any]): 包含代理信息的字典。
    Returns:
        Optional[Dict[str, Any]]: 转换后的 Clash 格式代理字典；如果无法转换，返回 None。
    """
    # 优先使用代理字典中已有的 Clash 兼容字段
    if proxy.get('type') and proxy.get('server') and proxy.get('port'):
        clash_proxy = {
            'name': proxy.get('ps', f"{proxy['type']}-{proxy['server']}:{proxy['port']}"), # 代理名称
            'type': proxy['type'], # 协议类型
            'server': proxy['server'], # 服务器地址
            'port': proxy['port'], # 端口
        }
        # 根据协议类型添加 Clash 需要的特定字段
        if 'uuid' in proxy: clash_proxy['uuid'] = proxy['uuid']
        if 'alterId' in proxy: clash_proxy['alterId'] = proxy['alterId']
        if 'cipher' in proxy: clash_proxy['cipher'] = proxy['cipher']
        if 'password' in proxy: clash_proxy['password'] = proxy['password']
        if 'tls' in proxy: clash_proxy['tls'] = proxy['tls']
        if 'network' in proxy: clash_proxy['network'] = proxy['network']
        if 'ws-path' in proxy: clash_proxy['ws-path'] = proxy['ws-path']
        if 'ws-headers' in proxy: clash_proxy['ws-headers'] = proxy['ws-headers']
        if 'flow' in proxy: clash_proxy['flow'] = proxy['flow']
        if 'servername' in proxy: clash_proxy['servername'] = proxy['servername'] # SNI
        if 'grpc-serviceName' in proxy: clash_proxy['grpc-serviceName'] = proxy['grpc-serviceName']
        if 'grpc-mode' in proxy: clash_proxy['grpc-mode'] = proxy['grpc-mode']

        # Hysteria2 特有字段
        if proxy['type'] == 'hysteria2':
            if 'skip-cert-verify' in proxy: clash_proxy['skip-cert-verify'] = proxy['skip-cert-verify']
            # 其他 Hysteria2 字段（如 up/down Mbps, autoup, obfs, obfs-password）需要根据您的解析器提供的数据添加

        # TUIC 特有字段
        if proxy['type'] == 'tuic':
            if 'tuic_version' in proxy: clash_proxy['version'] = proxy['tuic_version'] # Clash uses 'version'
            if 'udp-relay-mode' in proxy: clash_proxy['udp-relay-mode'] = proxy['udp-relay-mode']
            if 'disable-sni' in proxy: clash_proxy['disable-sni'] = proxy['disable-sni']
            if 'congestion-controller' in proxy: clash_proxy['congestion-controller'] = proxy['congestion-controller']
            if 'alpn' in proxy: clash_proxy['alpn'] = proxy['alpn']
            if 'skip-cert-verify' in proxy: clash_proxy['skip-cert-verify'] = proxy['skip-cert-verify']

        # Clash 额外参数：
        # 对于 VLESS/Trojan 等，如果需要配置 UDP 转发，可能需要设置 `udp: true`
        # 部分协议 Clash 默认支持 UDP，部分需要明确声明
        # 例如，对于支持 UDP 的协议，可以考虑添加: clash_proxy['udp'] = True

        return clash_proxy
    
    logger.warning(f"无法将代理转换为 Clash 格式，跳过: {proxy.get('ps', '未知代理')}")
    return None # 返回 None 如果无法转换或不支持的格式

def write_proxies_to_clash_yaml(proxies: List[Dict[str, Any]]):
    """
    将验证通过的代理列表写入 Clash YAML 配置文件。
    Args:
        proxies (List[Dict[str, Any]]): 包含代理信息的字典列表。
    """
    _ensure_output_dir_exists() # 确保输出目录存在
    output_path = os.path.join(config.OUTPUT_DIR, config.CLASH_OUTPUT_FILENAME)

    clash_proxies = []
    for proxy in proxies:
        clash_format = _convert_to_clash_format(proxy) # 将每个代理转换为 Clash 格式
        if clash_format:
            clash_proxies.append(clash_format)
        else:
            logger.warning(f"代理转换 Clash 格式失败，跳过输出: {proxy.get('ps', '未知代理')}")

    # 构建基本的 Clash 配置文件结构
    clash_config = {
        'proxies': clash_proxies, # 所有转换成功的代理节点
        'proxy-groups': [ # 代理组配置
            {
                'name': 'Proxy', # 代理组名称
                'type': 'select', # 选择类型（用户手动选择）
                # 代理组包含 'DIRECT'（直连）和所有已命名的代理
                'proxies': ['DIRECT'] + [p['name'] for p in clash_proxies if 'name' in p]
            },
            # 您可以在这里添加更多代理组，例如 '自动选择'、'故障转移' 等
            # 示例：
            # {
            #     'name': 'Auto Select',
            #     'type': 'url-test',
            #     'proxies': [p['name'] for p in clash_proxies if 'name' in p],
            #     'url': 'http://www.gstatic.com/generate_204',
            #     'interval': 300
            # },
        ],
        'rules': [ # 规则配置
            'MATCH,Proxy' # 默认规则：所有未匹配的流量都通过 'Proxy' 组
        ],
        # 您可以在这里添加其他 Clash 配置，例如：
        # 'log-level': 'info',
        # 'mode': 'rule',
        # 'external-controller': '127.0.0.1:9090',
        # 'dns': {
        #     'enable': True,
        #     'nameserver': ['114.114.114.114', '8.8.8.8'],
        #     'fallback': ['1.1.1.1', '8.8.4.4'],
        #     'fallback-filter': {
        #         'geoip': True,
        #         'geosite': True
        #     }
        # }
    }

    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            # 将 Python 字典转换为 YAML 格式并写入文件
            yaml.dump(clash_config, f, allow_unicode=True, sort_keys=False)
        logger.info(f"成功将 {len(clash_proxies)} 个代理写入 Clash YAML 文件: {output_path}")
    except IOError as e:
        logger.error(f"写入 Clash YAML 文件失败: {e}")
    except yaml.YAMLError as e:
        logger.error(f"生成 Clash YAML 配置时发生 YAML 错误: {e}")
