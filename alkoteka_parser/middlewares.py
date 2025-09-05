# Define here the models for your spider middleware
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/spider-middleware.html

import logging
import base64
import random
from typing import List
from scrapy import signals
from scrapy.exceptions import NotConfigured


class RotateUserAgentMiddleware:
    """Middleware для ротации User-Agent"""

    def __init__(self, user_agents):
        self.user_agents = user_agents

    @classmethod
    def from_crawler(cls, crawler):
        user_agents = crawler.settings.getlist('USER_AGENTS')
        if not user_agents:
            raise NotConfigured('USER_AGENTS not configured')
        return cls(user_agents)

    def process_request(self, request, spider):
        ua = random.choice(self.user_agents)
        request.headers['User-Agent'] = ua
        spider.logger.debug(f'Using User-Agent: {ua[:50]}...')


class ProxyMiddleware:
    """
    Enhanced proxy middleware with better error handling
    """

    def __init__(self, settings):
        self.logger = logging.getLogger(__name__)
        self.enabled = settings.getbool('PROXY_ENABLED', False)

        if not self.enabled:
            self.logger.info("Proxy middleware disabled")
            return

        self.mode = settings.get('PROXY_MODE', 'rotating')
        self.proxy_auth = settings.get('PROXY_AUTH', '')
        self.failed_proxies = set()  # Track failed proxies
        self.max_failures = 3  # Max failures before removing proxy

        if self.mode == 'rotating':
            self.proxies = self._load_proxies(settings)
            self.proxy_failures = {}  # Track failure count per proxy
            self.current_proxy_index = 0

            if not self.proxies:
                self.logger.warning("No proxies loaded, disabling middleware")
                self.enabled = False
        else:
            # Single proxy endpoint
            self.proxy_endpoint = settings.get('PROXY_ENDPOINT', '')
            if not self.proxy_endpoint:
                self.logger.warning("PROXY_ENDPOINT not configured")
                self.enabled = False

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings)

    def _load_proxies(self, settings) -> List[str]:
        """Load proxies from file or settings"""
        proxies = []

        # Try loading from file first
        proxy_file = settings.get('PROXY_LIST_FILE', 'proxy_list.txt')
        try:
            with open(proxy_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        proxy = self._normalize_proxy(line)
                        if proxy:
                            proxies.append(proxy)
            self.logger.info(f"Loaded {len(proxies)} proxies from {proxy_file}")
        except FileNotFoundError:
            self.logger.debug(f"Proxy file {proxy_file} not found")
        except Exception as e:
            self.logger.error(f"Error loading proxies from file: {e}")

        # If no proxies from file, try from settings
        if not proxies:
            proxy_list = settings.getlist('PROXY_LIST', [])
            for proxy in proxy_list:
                normalized = self._normalize_proxy(proxy)
                if normalized:
                    proxies.append(normalized)
            if proxies:
                self.logger.info(f"Loaded {len(proxies)} proxies from settings")

        return proxies

    def _normalize_proxy(self, proxy: str) -> str:
        """Normalize proxy URL format"""
        proxy = proxy.strip()
        if not proxy:
            return None

        # Add protocol if missing
        if '://' not in proxy:
            # Assume HTTP if no protocol specified
            proxy = f'http://{proxy}'

        # Validate basic format
        if proxy.startswith(('http://', 'https://', 'socks4://', 'socks5://')):
            return proxy

        self.logger.warning(f"Invalid proxy format: {proxy}")
        return None

    def process_request(self, request, spider):
        if not self.enabled:
            return

        # Skip if proxy already set (e.g., by retry)
        if 'proxy' in request.meta:
            return

        proxy = None

        if self.mode == 'rotating' and self.proxies:
            # Get next working proxy
            proxy = self._get_next_proxy()
            if not proxy:
                self.logger.error("No working proxies available")
                self.enabled = False
                return

            request.meta['proxy'] = proxy
            request.meta['proxy_retry_times'] = 0  # Track retries per request

            # Add authentication if needed
            if self.proxy_auth and '@' not in proxy:
                self._set_proxy_auth(request)

        elif self.proxy_endpoint:
            # Use single endpoint
            request.meta['proxy'] = self.proxy_endpoint
            if self.proxy_auth:
                self._set_proxy_auth(request)
            proxy = self.proxy_endpoint

        if proxy:
            spider.logger.debug(f"Using proxy: {proxy}")

    def _get_next_proxy(self) -> str:
        """Get next working proxy from rotation"""
        attempts = 0
        max_attempts = len(self.proxies) * 2

        while attempts < max_attempts:
            if not self.proxies:
                return None

            # Get next proxy in rotation
            proxy = self.proxies[self.current_proxy_index % len(self.proxies)]
            self.current_proxy_index += 1
            attempts += 1

            # Skip if proxy has too many failures
            if self.proxy_failures.get(proxy, 0) < self.max_failures:
                return proxy

        return None

    def _set_proxy_auth(self, request):
        """Set proxy authentication header"""
        if self.proxy_auth:
            # Handle different auth formats
            if ':' in self.proxy_auth:
                encoded_auth = base64.b64encode(self.proxy_auth.encode()).decode('ascii')
                request.headers['Proxy-Authorization'] = f'Basic {encoded_auth}'
            else:
                self.logger.warning("Invalid proxy auth format. Expected 'username:password'")

    def process_exception(self, request, exception, spider):
        """Handle proxy failures"""

        if 'proxy' not in request.meta:
            return

        proxy = request.meta['proxy']

        # Log the failure
        spider.logger.warning(f"Proxy {proxy} failed with {type(exception).__name__}: {exception}")

        if self.mode == 'rotating':
            # Increment failure count
            self.proxy_failures[proxy] = self.proxy_failures.get(proxy, 0) + 1

            # Remove proxy if it failed too many times
            if self.proxy_failures[proxy] >= self.max_failures:
                if proxy in self.proxies:
                    self.proxies.remove(proxy)
                    spider.logger.warning(f"Removed failed proxy {proxy}. {len(self.proxies)} proxies remaining")

                    # Disable if no proxies left
                    if not self.proxies:
                        self.enabled = False
                        spider.logger.error("No working proxies left, disabling proxy middleware")

        # Allow retry with different proxy
        request.meta.pop('proxy', None)
        request.meta['proxy_retry_times'] = request.meta.get('proxy_retry_times', 0) + 1

        # Don't retry same request too many times
        if request.meta['proxy_retry_times'] < 3:
            return request


class AlkotekaParserSpiderMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the spider middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_spider_input(self, response, spider):
        # Called for each response that goes through the spider
        # middleware and into the spider.

        # Should return None or raise an exception.
        return None

    def process_spider_output(self, response, result, spider):
        # Called with the results returned from the Spider, after
        # it has processed the response.

        # Must return an iterable of Request, or item objects.
        for i in result:
            yield i

    def process_spider_exception(self, response, exception, spider):
        # Called when a spider or process_spider_input() method
        # (from other spider middleware) raises an exception.

        # Should return either None or an iterable of Request or item objects.
        pass

    def process_start_requests(self, start_requests, spider):
        # Called with the start requests of the spider, and works
        # similarly to the process_spider_output() method, except
        # that it doesn’t have a response associated.

        # Must return only requests (not items).
        for r in start_requests:
            yield r

    def spider_opened(self, spider):
        spider.logger.info("Spider opened: %s" % spider.name)


class AlkotekaParserDownloaderMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the downloader middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_request(self, request, spider):
        # Called for each request that goes through the downloader
        # middleware.

        # Must either:
        # - return None: continue processing this request
        # - or return a Response object
        # - or return a Request object
        # - or raise IgnoreRequest: process_exception() methods of
        #   installed downloader middleware will be called
        return None

    def process_response(self, request, response, spider):
        # Called with the response returned from the downloader.

        # Must either;
        # - return a Response object
        # - return a Request object
        # - or raise IgnoreRequest
        return response

    def process_exception(self, request, exception, spider):
        # Called when a download handler or a process_request()
        # (from other downloader middleware) raises an exception.

        # Must either:
        # - return None: continue processing this exception
        # - return a Response object: stops process_exception() chain
        # - return a Request object: stops process_exception() chain
        pass

    def spider_opened(self, spider):
        spider.logger.info("Spider opened: %s" % spider.name)


