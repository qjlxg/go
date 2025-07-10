# config.py

# 代理源列表，程序将从这些 URL 抓取代理信息
# 您可以在这里添加或删除代理源
PROXY_SOURCES = [
    "https://raw.githubusercontent.com/mahdibland/ShadowsocksAggregator/master/sub/sub_merge.txt",
    "https://raw.githubusercontent.com/freefq/free/master/v2",
    "https://raw.githubusercontent.com/ermaozi/get_proxy/main/proxy_vless.txt",
    "https://raw.githubusercontent.com/ermaozi/get_proxy/main/proxy_vmess.txt",
    "https://raw.githubusercontent.com/ermaozi/get_proxy/main/proxy_ss.txt",
    "https://raw.githubusercontent.com/ermaozi/get_proxy/main/proxy_trojan.txt",
    "https://raw.githubusercontent.com/ermaozi/get_proxy/main/proxy_hy2.txt",
    "https://raw.githubusercontent.com/ermaozi/get_proxy/main/proxy_tuic.txt",
    "https://raw.githubusercontent.com/barry-far/V2ray-Configs/main/All.txt",
    "https://raw.githubusercontent.com/changfengoss/VPS/main/VLESS.txt",
    "https://raw.githubusercontent.com/changfengoss/VPS/main/VMess.txt",
    "https://raw.githubusercontent.com/changfengoss/VPS/main/SS.txt",
    "https://raw.githubusercontent.com/changfengoss/VPS/main/Trojan.txt",
    # 添加更多代理源...
]

# 抓取和验证代理时的超时时间（秒）
# FETCH_TIMEOUT 用于从代理源抓取内容时的超时
FETCH_TIMEOUT = 10 
# PROXY_CHECK_TIMEOUT 用于检查代理 TCP 连通性时的超时
PROXY_CHECK_TIMEOUT = 5

# 最大并发检查数量
# 较高的值可以加快验证速度，但可能增加对服务器的压力
MAX_CONCURRENT_CHECKS = 50 

# 输出目录和文件名
OUTPUT_DIR = "output" # 输出文件将保存在此目录下
PLAIN_TEXT_OUTPUT_FILENAME = "proxies.txt" # 明文代理列表的文件名
CLASH_OUTPUT_FILENAME = "clash_config.yaml" # Clash 配置文件的文件名

# 筛选通过验证的代理数量，设置为 None 或 0 表示输出所有有效代理
# 例如，如果您只想输出延迟最低的前 100 个代理，设置为 100
TOP_N_PROXIES = None # 或设置为一个整数，如 100

# 控制 Trojan 代理去重时是否考虑密码
# 如果设置为 True，则密码不同的 Trojan 代理会被认为是不同的代理。
# 如果设置为 False，即使密码不同，只要服务器地址和端口相同，就可能被视为同一个代理。
# 默认为 False，通常代理去重不依赖密码，因为密码可能只是随机生成。
DEDUPLICATE_BY_PASSWORD_TROJAN = False

# 是否启用 HTTP/HTTPS 可访问性检查。如果设置为 True，代理将尝试访问 TEST_HTTP_URL。
# 只有当 TCP 连通性检查和 HTTP/HTTPS 访问检查都通过时，代理才会被视为有效。
ENABLE_HTTP_CHECK = True 

# 用于 HTTP/HTTPS 可访问性检查的测试 URL。
# 建议使用一个稳定、可靠且不易被墙的网站，例如 Google 或 GitHub。
TEST_HTTP_URL = "https://www.google.com" # 或者 "https://github.com"

# HTTP/HTTPS 可访问性检查的超时时间（秒）。
# 如果在此时间内无法通过代理访问 TEST_HTTP_URL，则认为该代理无法通过 HTTP 检查。
HTTP_CHECK_TIMEOUT = 10 # 可以根据需要调整
