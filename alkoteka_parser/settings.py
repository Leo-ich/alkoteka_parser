# Scrapy settings for alkoteka_parser project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://docs.scrapy.org/en/latest/topics/settings.html
#     https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://docs.scrapy.org/en/latest/topics/spider-middleware.html

BOT_NAME = "alkoteka_parser"

SPIDER_MODULES = ["alkoteka_parser.spiders"]
NEWSPIDER_MODULE = "alkoteka_parser.spiders"


# Crawl responsibly by identifying yourself (and your website) on the user-agent
#USER_AGENT = "alkoteka_parser"

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

# Configure maximum concurrent requests performed by Scrapy (default: 16)
CONCURRENT_REQUESTS = 4

# Configure a delay for requests for the same website (default: 0)
# See https://docs.scrapy.org/en/latest/topics/settings.html#download-delay
# See also autothrottle settings and docs
DOWNLOAD_DELAY = 2
RANDOMIZE_DOWNLOAD_DELAY = True
# The download delay setting will honor only one of:
CONCURRENT_REQUESTS_PER_DOMAIN = 2
#CONCURRENT_REQUESTS_PER_IP = 16

# Download timeout
DOWNLOAD_TIMEOUT = 20

# Disable cookies (enabled by default)
COOKIES_ENABLED = True

# Disable Telnet Console (enabled by default)
TELNETCONSOLE_ENABLED = False

# Override the default request headers:
DEFAULT_REQUEST_HEADERS = {
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
    'Accept-Encoding': 'gzip, deflate, br',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
    'Origin': 'https://alkoteka.com',
    'Referer': 'https://alkoteka.com/',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-origin',
}

# Enable or disable spider middlewares
# See https://docs.scrapy.org/en/latest/topics/spider-middleware.html
#SPIDER_MIDDLEWARES = {
#    "alkoteka_parser.middlewares.AlkotekaParserSpiderMiddleware": 543,
#}

# Enable or disable downloader middlewares
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
DOWNLOADER_MIDDLEWARES = {
#    "alkoteka_parser.middlewares.AlkotekaParserDownloaderMiddleware": 543,
}

# Enable or disable extensions
# See https://docs.scrapy.org/en/latest/topics/extensions.html
#EXTENSIONS = {
#    "scrapy.extensions.telnet.TelnetConsole": None,
#}

# Configure item pipelines
# See https://docs.scrapy.org/en/latest/topics/item-pipeline.html
ITEM_PIPELINES = {
    'alkoteka_parser.pipelines.ValidationPipeline': 200,
    'alkoteka_parser.pipelines.DataCleaningPipeline': 300,
}

# Enable and configure the AutoThrottle extension (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/autothrottle.html
#AUTOTHROTTLE_ENABLED = True
# The initial download delay
#AUTOTHROTTLE_START_DELAY = 5
# The maximum download delay to be set in case of high latencies
#AUTOTHROTTLE_MAX_DELAY = 60
# The average number of requests Scrapy should be sending in parallel to
# each remote server
#AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
# Enable showing throttling stats for every response received:
#AUTOTHROTTLE_DEBUG = False

# Enable and configure HTTP caching (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings
HTTPCACHE_ENABLED = True
HTTPCACHE_EXPIRATION_SECS = 3600*24     # 24 hour
HTTPCACHE_DIR = "httpcache"
HTTPCACHE_IGNORE_HTTP_CODES = [503, 504, 400, 403, 404]
HTTPCACHE_STORAGE = "scrapy.extensions.httpcache.FilesystemCacheStorage"

# Minimum level to log. Available levels are: CRITICAL, ERROR, WARNING, INFO, DEBUG
LOG_LEVEL = 'INFO'
COOKIES_DEBUG = False

# Retry configuration
RETRY_ENABLED = True
RETRY_TIMES = 0
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]

# Set settings whose default value is deprecated to a future-proof value
REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEED_EXPORT_ENCODING = "utf-8"
FEED_EXPORT_INDENT = 2

# City/Region settings
TARGET_CITY_NAME = 'Краснодар'  # City name to parse
INITIAL_CITY_UUID = '4a70f9e0-46ae-11e7-83ff-00155d026416'  # Initial UUID for city API

# API settings
API_BASE_URL = 'https://alkoteka.com/web-api/v1'
API_PRODUCTS_ENDPOINT = '/product'
API_CITY_ENDPOINT = '/city'
API_PER_PAGE = 20

# Parser settings
PARSE_PRODUCT_DETAILS = True  # Whether to visit product pages for additional data

# Proxy settings (optional)
PROXY_ENABLED = False  # Set to True to enable proxy
PROXY_MODE = 'rotating'  # 'rotating' or 'single'
PROXY_ENDPOINT = ''  # For services with automatic IP rotation
PROXY_AUTH = ''  # 'username:password' if needed
PROXY_LIST = [
    # Add your proxy list here
    # 'http://proxy1:port',
    # 'http://proxy2:port',
]
