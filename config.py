# proxy_tool/config.py

# --- Scraper Configuration ---
# List of URLs to fetch raw proxy links from.
# You can add or remove URLs here.
# These can be plain text lists, base64 encoded strings, or Clash YAMLs.
PROXY_SOURCES = [
    "https://raw.githubusercontent.com/freefq/free/master/v2", # Example for Vmess/Vless/Trojan links
    "https://raw.githubusercontent.com/barry-far/V2ray-Configs/main/All_Configs_Sub.txt", # Example base64 encoded
    "https://raw.githubusercontent.com/cclz8899/Clash-Rule/main/Sub.yaml", # Example Clash YAML
    "https://raw.githubusercontent.com/qjlxg/hy2/refs/heads/main/configtg.txt", # Add your own sources here
]

# --- Parser Configuration ---
# Timeout for fetching raw proxy content from sources (in seconds)
FETCH_TIMEOUT = 10

# --- Validator Configuration ---
# Timeout for checking individual proxy latency (in seconds)
PROXY_CHECK_TIMEOUT = 5

# Maximum number of concurrent proxy checks
# Adjust based on your network and CPU capabilities to avoid overloading.
MAX_CONCURRENT_CHECKS = 50

# URL for IP information API (e.g., to get region/ISP).
# Note: Free APIs might have rate limits (HTTP 429). Consider using a stable one.
# This example uses ip-api.com, which has rate limits for free tier (45 requests/minute for non-commercial use).
# For more robust solutions, consider paid APIs or running your own IP lookup service.
IP_API_URL = "http://ip-api.com/json/{ip}?lang=zh-CN&fields=country,countryCode,regionName,city,isp,query"

# --- Output Configuration ---
# Directory to save the output files
OUTPUT_DIR = "output"

# Filename for the validated proxies in JSON format
JSON_OUTPUT_FILENAME = "validated_proxies.json"

# Filename for the validated proxies in Clash YAML format
CLASH_OUTPUT_FILENAME = "clash_config.yaml"

# Top N proxies to include in the output files (sorted by latency)
TOP_N_PROXIES = 200 # Set to None to include all validated proxies
