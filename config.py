# proxy_tool/config.py

# --- Scraper Configuration ---
# List of URLs to fetch raw proxy links from.
# You can add or remove URLs here.
# These can be plain text lists, base64 encoded strings, or Clash YAMLs.
PROXY_SOURCES = [
    "https://raw.githubusercontent.com/qjlxg/ss/refs/heads/master/list_raw.txt", 
    "https://raw.githubusercontent.com/qjlxg/vt/refs/heads/main/data/nodes.txt", 
    "https://raw.githubusercontent.com/cclz8899/Clash-Rule/main/Sub.yaml", 
    "https://raw.githubusercontent.com/qjlxg/hy2/refs/heads/main/configtg.txt", 
    "https://raw.githubusercontent.com/qjlxg/aggregator/refs/heads/main/data/clash.yaml",
    "https://raw.githubusercontent.com/qjlxg/aggregator/refs/heads/main/data/520.yaml",
    "https://raw.githubusercontent.com/qjlxg/aggregator/refs/heads/main/ss.txt",
    "https://raw.githubusercontent.com/qjlxg/collectSub/refs/heads/main/config_all_merged_nodes.txt",
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
TOP_N_PROXIES = 9000 # Set to None to include all validated proxies
