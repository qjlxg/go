# proxy_tool/output/writer.py

import json
import yaml
import os
import logging
from typing import List

from models.proxy_model import Proxy # Import the Proxy model
import config # Import config for output directory and filenames

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ProxyWriter:
    def __init__(self):
        # Ensure the output directory exists
        os.makedirs(config.OUTPUT_DIR, exist_ok=True)

    def write_proxies_to_json(self, proxies: List[Proxy], filename: str = config.JSON_OUTPUT_FILENAME):
        """
        Writes a list of Proxy objects to a JSON file.
        Each proxy is converted to its dictionary representation.
        """
        output_path = os.path.join(config.OUTPUT_DIR, filename)
        proxy_dicts = [p.to_dict() for p in proxies] # Convert Proxy objects to dictionaries

        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(proxy_dicts, f, ensure_ascii=False, indent=4)
            logging.info(f"成功将 {len(proxies)} 个代理写入 JSON 文件: {output_path}")
        except IOError as e:
            logging.error(f"写入 JSON 文件失败 {output_path}: {e}")
        except Exception as e:
            logging.error(f"写入 JSON 文件时发生意外错误 {output_path}: {e}")

    def write_proxies_to_clash_yaml(self, proxies: List[Proxy], filename: str = config.CLASH_OUTPUT_FILENAME):
        """
        Writes a list of Proxy objects into a Clash-compatible YAML configuration.
        """
        output_path = os.path.join(config.OUTPUT_DIR, filename)
        
        # Prepare the Clash proxies list
        clash_proxies_list = [p.to_clash_proxy_dict() for p in proxies]
        
        # Create a basic Clash config structure
        clash_config = {
            "proxies": clash_proxies_list,
            # You can add basic proxy groups or other Clash config here if needed
            # For simplicity, we only include the proxies list for now.
            # Example for a simple proxy group:
            "proxy-groups": [
                {
                    "name": "Proxy",
                    "type": "select",
                    "proxies": [p.name for p in proxies] # Use names of generated proxies
                },
                {
                    "name": "Fallback",
                    "type": "fallback",
                    "url": "http://www.google.com/generate_204", # Example test URL
                    "interval": 300,
                    "proxies": [p.name for p in proxies]
                },
                {
                    "name": "Auto",
                    "type": "url-test",
                    "url": "http://www.google.com/generate_204",
                    "interval": 300,
                    "proxies": [p.name for p in proxies]
                }
            ],
            "rules": [
                "MATCH,Proxy" # Default rule to use the 'Proxy' group
            ]
        }
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                yaml.dump(clash_config, f, allow_unicode=True, indent=2, sort_keys=False)
            logging.info(f"成功将 {len(proxies)} 个代理写入 Clash YAML 文件: {output_path}")
        except IOError as e:
            logging.error(f"写入 Clash YAML 文件失败 {output_path}: {e}")
        except Exception as e:
            logging.error(f"写入 Clash YAML 文件时发生意外错误 {output_path}: {e}")
