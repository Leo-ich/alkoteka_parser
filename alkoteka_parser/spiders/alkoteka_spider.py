
import math
import scrapy
import json
import time
import re
from typing import Dict, List, Any, Optional
from urllib.parse import urlencode
from alkoteka_parser.items import AlkotekaItem


class AlkotekaSpider(scrapy.Spider):
    """Spider for parsing Alkoteka products through API"""

    name = 'alkoteka'
    allowed_domains = ['alkoteka.com']

    # Default values (will be overridden from settings)
    api_base = 'https://alkoteka.com/web-api/v1'
    products_endpoint = '/product'
    city_endpoint = '/city'
    target_city_name = 'Краснодар'
    initial_city_uuid = '4a70f9e0-46ae-11e7-83ff-00155d026416'
    per_page = 20
    parse_details = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # City UUID will be determined from city API
        self.city_uuid = None

        # Statistics
        self.products_count = 0
        self.cities_found = []
        self.start_time = time.time()

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        """Initialize spider with settings from crawler"""
        spider = super(AlkotekaSpider, cls).from_crawler(crawler, *args, **kwargs)

        # Get settings
        spider.api_base = crawler.settings.get('API_BASE_URL', spider.api_base)
        spider.products_endpoint = crawler.settings.get('API_PRODUCTS_ENDPOINT', spider.products_endpoint)
        spider.city_endpoint = crawler.settings.get('API_CITY_ENDPOINT', spider.city_endpoint)
        spider.target_city_name = crawler.settings.get('TARGET_CITY_NAME', spider.target_city_name)
        spider.initial_city_uuid = crawler.settings.get('INITIAL_CITY_UUID', spider.initial_city_uuid)
        spider.per_page = crawler.settings.getint('API_PER_PAGE', spider.per_page)
        spider.parse_details = crawler.settings.getbool('PARSE_PRODUCT_DETAILS', spider.parse_details)

        return spider

    def start_requests(self):
        """Start by fetching all cities to find target city UUID"""

        self.logger.info(f"Starting parser. Target city: {self.target_city_name}")

        # Start fetching cities
        city_url = f"{self.api_base}{self.city_endpoint}"
        params = {
            'city_uuid': self.initial_city_uuid,
            'page': 1
        }

        yield scrapy.Request(
            url=f"{city_url}?{urlencode(params)}",
            callback=self.parse_cities,
            meta={
                'page': 1,
                'city_url': city_url,
                'dont_cache': True
            },
            errback=self.handle_error,
            dont_filter=True
        )

    def parse_cities(self, response):
        """Parse city API response to find target city UUID"""

        if response.status != 200:
            self.logger.error(f"City API returned status {response.status}")
            # Fall back to initial UUID
            self.city_uuid = self.initial_city_uuid
            yield from self.start_category_parsing()
            return

        try:
            data = json.loads(response.text)
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse city JSON: {e}")
            self.city_uuid = self.initial_city_uuid
            yield from self.start_category_parsing()
            return

        if not data.get('success'):
            self.logger.error("City API returned success=false")
            self.city_uuid = self.initial_city_uuid
            yield from self.start_category_parsing()
            return

        # Collect cities from results and accented lists
        cities = []

        # Add regular results
        results = data.get('results', [])
        cities.extend(results)

        # Store found cities
        for city in cities:
            city_info = {
                'name': city.get('name'),
                'uuid': city.get('uuid'),
                'slug': city.get('slug')
            }
            if city_info not in self.cities_found:
                self.cities_found.append(city_info)

            # Check if this is our target city
            if city.get('name') == self.target_city_name:
                self.city_uuid = city.get('uuid')
                self.logger.info(
                    f"Found target city '{self.target_city_name}' "
                    f"with UUID: {self.city_uuid}"
                )

        # Check pagination
        meta_info = data.get('meta', {})
        current_page = meta_info.get('current_page', 1)
        has_more = meta_info.get('has_more_pages', False)

        self.logger.info(
            f"City API page {current_page}: "
            f"Found {len(cities)} cities "
            f"(total collected: {len(self.cities_found)})"
        )

        # If we haven't found the target city yet and there are more pages
        if not self.city_uuid and has_more:
            next_page = current_page + 1
            params = {
                'city_uuid': self.initial_city_uuid,
                'page': next_page
            }

            yield scrapy.Request(
                url=f"{response.meta['city_url']}?{urlencode(params)}",
                callback=self.parse_cities,
                meta={
                    'page': next_page,
                    'city_url': response.meta['city_url'],
                    'dont_cache': True
                },
                errback=self.handle_error,
                dont_filter=True
            )
        else:
            # Finished collecting cities
            if self.city_uuid:
                self.logger.info(
                    f"Successfully found target city. "
                    f"Total cities discovered: {len(self.cities_found)}"
                )
            else:
                self.logger.warning(
                    f"Target city '{self.target_city_name}' not found in {len(self.cities_found)} cities. "
                    f"Using initial UUID: {self.initial_city_uuid}"
                )
                self.city_uuid = self.initial_city_uuid

            # Start parsing categories
            yield from self.start_category_parsing()

    def start_category_parsing(self):
        """Start parsing product categories"""

        categories = self._load_categories()
        self.logger.info(
            f"Starting product parsing for {len(categories)} categories "
            f"using city UUID: {self.city_uuid}"
        )

        for category_url in categories:
            category_slug = self._extract_category_slug(category_url)
            if not category_slug:
                self.logger.warning(f"Could not extract slug from {category_url}")
                continue

            # Create API request for first page of category
            yield self._create_product_list_request(
                category_slug=category_slug,
                page=1,
                category_url=category_url
            )

    def _load_categories(self) -> List[str]:
        """Load category URLs from file or use defaults"""

        default_urls = [
            'https://alkoteka.com/catalog/slaboalkogolnye-napitki-2',
            'https://alkoteka.com/catalog/vino',
            'https://alkoteka.com/catalog/krepkiy-alkogol',
        ]

        try:
            with open('categories.txt', 'r', encoding='utf-8') as f:
                urls = []
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        urls.append(line)

                if urls:
                    self.logger.info(f"Loaded {len(urls)} categories from file")
                    return urls
        except FileNotFoundError:
            self.logger.info("categories.txt not found, using default URLs")
        except Exception as e:
            self.logger.error(f"Error reading categories file: {e}")

        return default_urls

    def _extract_category_slug(self, url: str) -> Optional[str]:
        """Extract category slug from URL"""

        parts = url.rstrip('/').split('/')
        if 'catalog' in parts:
            idx = parts.index('catalog')
            if idx + 1 < len(parts):
                return parts[idx + 1]
        return None

    def _create_product_list_request(
        self,
        category_slug: str,
        page: int,
        category_url: str
    ) -> scrapy.Request:
        """Create API request for product list"""

        params = {
            'city_uuid': self.city_uuid,
            'page': page,
            'per_page': self.per_page,
            'root_category_slug': category_slug
        }

        url = f"{self.api_base}{self.products_endpoint}?{urlencode(params)}"

        return scrapy.Request(
            url=url,
            callback=self.parse_product_list,
            headers={
                'Accept': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': category_url,
            },
            meta={
                'category_slug': category_slug,
                'page': page,
                'category_url': category_url,
                'handle_httpstatus_list': [403, 429, 503]
            },
            errback=self.handle_error,
            dont_filter=True
        )

    def parse_product_list(self, response):
        """Parse product list from API response"""

        if response.status != 200:
            self.logger.warning(
                f"Product list API returned status {response.status} "
                f"for category {response.meta.get('category_slug')}"
            )

            # Retry logic
            if response.status in [403, 429]:
                retry_count = response.meta.get('retry_count', 0)
                if retry_count < 3:
                    self.logger.info(f"Retrying request (attempt {retry_count + 1})")
                    request = response.request.copy()
                    request.meta['retry_count'] = retry_count + 1
                    request.dont_filter = True
                    yield request
            return

        try:
            data = json.loads(response.text)
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse product list JSON: {e}")
            return

        if not isinstance(data, dict) or not data.get('success'):
            self.logger.error(f"Invalid product list response")
            return

        # Extract products
        products = data.get('results', [])
        meta_info = data.get('meta', {})

        number_pages = '?'
        if meta_info.get('total') and meta_info.get('per_page'):
            try:
                number_pages = math.ceil(int(meta_info.get('total'))/int(meta_info.get('per_page')))
            except ValueError:
                number_pages = '?'

        self.logger.info(
            f"Category '{response.meta['category_slug']}' "
            f"page {meta_info.get('current_page', '?')}/{number_pages}: "
            f"Found {len(products)} products (total: {meta_info.get('total', '?')})"
        )

        # Process each product
        for product_data in products:
            if self.parse_details:
                # Create request to product detail page
                product_slug = product_data.get('slug')

                if product_slug:
                    # Construct product detail API URL
                    product_identifier = f"{product_slug}"
                    product_detail_url = (
                        f"{self.api_base}{self.products_endpoint}/"
                        f"{product_identifier}?city_uuid={self.city_uuid}"
                    )

                    self.logger.debug(f"Requesting product details: {product_detail_url}")
                    yield scrapy.Request(
                        url=product_detail_url,
                        callback=self.parse_product_detail,
                        meta={
                            'product_list_data': product_data,
                            'category_url': response.meta['category_url'],
                            'handle_httpstatus_list': [404, 403, 429, 503]
                        },
                        errback=self.handle_product_error
                    )
            else:
                # Parse from list data only
                item = self._parse_product_from_list(product_data)
                if item:
                    self.products_count += 1
                    yield item

        # Pagination
        if meta_info.get('has_more_pages', False):
            next_page = meta_info.get('current_page', 1) + 1

            yield self._create_product_list_request(
                category_slug=response.meta['category_slug'],
                page=next_page,
                category_url=response.meta['category_url']
            )

    def parse_product_detail(self, response):
        """Parse detailed product information from product API"""

        list_data = response.meta.get('product_list_data', {})

        if response.status != 200:
            if response.status == 404:
                self.logger.debug(f"Product detail not found (404): {response.url}")
            else:
                self.logger.warning(f"Product detail API returned status {response.status}: {response.url}")

            # Fall back to list data
            if list_data:
                item = self._parse_product_from_list(list_data)
                if item:
                    self.products_count += 1
                    yield item
            return

        try:
            data = json.loads(response.text)
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse product detail JSON: {e}")
            # Fall back to list data
            if list_data:
                item = self._parse_product_from_list(list_data)
                if item:
                    self.products_count += 1
                    yield item
            return

        if not data.get('success'):
            self.logger.debug(f"Product detail API returned success=false: {response.url}")
            # Fall back to list data
            if list_data:
                item = self._parse_product_from_list(list_data)
                if item:
                    self.products_count += 1
                    yield item
            return

        # Parse detailed product data
        product_data = data.get('results', {})

        item = self._parse_product_from_detail(product_data, list_data)
        if item:
            self.products_count += 1
            yield item

    def handle_product_error(self, failure):
        """Handle errors for product detail requests"""

        request = failure.request
        list_data = request.meta.get('product_list_data')

        self.logger.debug(f"Product detail request failed: {failure.value}")

        # Fall back to list data
        if list_data:
            item = self._parse_product_from_list(list_data)
            if item:
                self.products_count += 1
                yield item

    def _check_volume_in_title(self, title: str) -> bool:
        """Check if volume is already present in title"""
        # Pattern to detect volume in various formats
        volume_pattern = r'\d+(?:[.,]\d+)?\s*(?:л|л\.|мл|ml|l|литр|миллилитр)'
        return bool(re.search(volume_pattern, title, re.IGNORECASE))

    def _parse_product_from_list(self, data: Dict[str, Any]) -> Optional[AlkotekaItem]:
        """Parse product from list API data"""

        if not data:
            return None

        item = AlkotekaItem()

        # Basic fields
        item['timestamp'] = int(time.time())
        item['RPC'] = str(data.get('uuid') or '')

        # URL - construct proper product URL
        product_url = data.get('product_url', '')
        item['url'] = product_url

        # Title - check if volume already exists before adding
        title = data.get('name', '')

        # Only add volume if it's not already in the title
        volume = self._extract_volume(data)
        if not self._check_volume_in_title(title):
            if volume:
                title = f"{title}, {volume}"
        item['title'] = title

        # Marketing tags
        item['marketing_tags'] = self._extract_marketing_tags(data)

        # Brand
        item['brand'] = self._extract_brand(data)

        # Section
        item['section'] = self._extract_section(data)

        # Price data
        item['price_data'] = self._extract_price_data(data)

        # Stock
        item['stock'] = self._extract_stock(data)

        # Assets
        item['assets'] = self._extract_assets(data)

        # Metadata (basic from list)
        item['metadata'] = self._extract_basic_metadata(data)

        # Variants
        item['variants'] = 0

        return item

    def _parse_product_from_detail(
        self,
        detail_data: Dict[str, Any],
        list_data: Dict[str, Any]
    ) -> Optional[AlkotekaItem]:
        """Parse product from detailed API data"""

        if not detail_data:
            return self._parse_product_from_list(list_data)

        item = AlkotekaItem()

        # Basic fields
        item['timestamp'] = int(time.time())
        item['RPC'] = str(detail_data.get('uuid') or '')

        # URL - construct proper product URL
        # Priority: list_data > construct from detail_data
        product_url = list_data.get('product_url', '')
        item['url'] = product_url

        # Title with volume from description blocks
        title = detail_data.get('name', '')

        # Only add volume if it's not already in the title
        if not self._check_volume_in_title(title):
            volume = None

            # Extract volume from description_blocks
            for block in detail_data.get('description_blocks', []):
                if block.get('code') == 'obem':
                    if block.get('min') is not None:
                        volume = f"{block['min']} л"
                    break

            if not volume:
                volume = self._extract_volume(detail_data)

            if volume:
                title = f"{title}, {volume}"
        item['title'] = title

        # Marketing tags
        tags = self._extract_marketing_tags(detail_data)

        # Add tags from filter_labels
        for label in detail_data.get('filter_labels', []):
            if isinstance(label, dict):
                filter_type = label.get('filter', '')
                if filter_type == 'dopolnitelno':
                    tag_title = label.get('title', '')
                    if tag_title and tag_title not in tags:
                        tags.append(tag_title)

        item['marketing_tags'] = tags

        # Brand from description_blocks
        brand = ''
        for block in detail_data.get('description_blocks', []):
            if block.get('code') == 'brend':
                values = block.get('values', [])
                if values and isinstance(values[0], dict):
                    brand = values[0].get('name', '')
                break

        if not brand:
            brand = self._extract_brand(detail_data)

        item['brand'] = brand

        # Section
        item['section'] = self._extract_section(detail_data)

        # Price data
        item['price_data'] = self._extract_price_data(detail_data)

        # Stock
        item['stock'] = self._extract_stock(detail_data)

        # Assets
        item['assets'] = self._extract_assets(detail_data)

        # Metadata (detailed)
        metadata = {}

        # Description from text_blocks
        for block in detail_data.get('text_blocks', []):
            if block.get('title') == 'Описание':
                metadata['__description'] = block.get('content', '')
                break

        if '__description' not in metadata:
            metadata['__description'] = detail_data.get('subname', '')

        # Extract all characteristics from description_blocks
        for block in detail_data.get('description_blocks', []):
            code = block.get('code', '')
            title = block.get('title', '')

            if code == 'obem':
                # Volume
                if block.get('min') is not None:
                    metadata['Объем'] = f"{block['min']} л"
            elif code == 'krepost':
                # Alcohol strength
                if block.get('min') is not None:
                    metadata['Крепость'] = f"{block['min']}%"
            elif code == 'proizvoditel':
                # Manufacturer
                values = block.get('values', [])
                if values and isinstance(values[0], dict):
                    metadata['Производитель'] = values[0].get('name', '')
            elif code == 'brend':
                # Brand
                values = block.get('values', [])
                if values and isinstance(values[0], dict):
                    metadata['Бренд'] = values[0].get('name', '')
            elif code == 'strana':
                # Country
                values = block.get('values', [])
                if values and isinstance(values[0], dict):
                    metadata['Страна'] = values[0].get('name', '')
            elif code == 'vid-upakovki':
                # Package type
                values = block.get('values', [])
                if values and isinstance(values[0], dict):
                    metadata['Вид упаковки'] = values[0].get('name', '')
            elif title:
                # Other characteristics
                values = block.get('values', [])
                if values:
                    if isinstance(values[0], dict):
                        metadata[title] = values[0].get('name', '')
                    else:
                        metadata[title] = str(values[0])

        # Add additional fields
        if detail_data.get('vendor_code'):
            metadata['Артикул'] = str(detail_data['vendor_code'])

        if detail_data.get('country_name'):
            if 'Страна' not in metadata:
                metadata['Страна'] = detail_data['country_name']

        if detail_data.get('country_code'):
            metadata['Код страны'] = detail_data['country_code']

        if detail_data.get('uuid'):
            metadata['UUID'] = detail_data['uuid']

        if detail_data.get('quantity_total'):
            metadata['Общее количество'] = str(detail_data['quantity_total'])

        if detail_data.get('gift_package') is not None:
            metadata['Подарочная упаковка'] = 'Да' if detail_data['gift_package'] else 'Нет'

        if detail_data.get('offline_price'):
            metadata['Офлайн цена'] = str(detail_data['offline_price'])

        item['metadata'] = metadata

        # Variants (count unique volumes/sizes if available)
        item['variants'] = self._count_variants(detail_data)

        return item

    def _extract_volume(self, data: Dict) -> Optional[str]:
        """Extract volume from various data fields"""

        # From filter_labels
        for label in data.get('filter_labels', []):
            if isinstance(label, dict) and label.get('filter') == 'obem':
                return label.get('title', '')

        # From subname
        subname = data.get('subname', '')
        if subname:
            volume_match = re.search(
                r'(\d+(?:[.,]\d+)?)\s*(л|л\.|мл|ml|l)\b',
                subname,
                re.IGNORECASE
            )
            if volume_match:
                return volume_match.group(0)

        return None

    def _extract_marketing_tags(self, data: Dict) -> List[str]:
        """Extract marketing tags from data"""

        tags = []

        # Boolean flags
        if data.get('new'):
            tags.append('Новинка')
        if data.get('recomended'):
            tags.append('Рекомендуемое')
        if data.get('axioma'):
            tags.append('Axioma')
        if data.get('enogram'):
            tags.append('Enogram')
        if data.get('gift_package'):
            tags.append('Подарочная упаковка')

        # Action labels
        for label in data.get('action_labels', []):
            if isinstance(label, dict):
                label_name = label.get('name') or label.get('text') or label.get('title', '')
                if label_name and label_name not in tags:
                    tags.append(label_name)

        return tags

    def _extract_brand(self, data: Dict) -> str:
        """Extract brand from data"""

        # Try from filter_labels
        for label in data.get('filter_labels', []):
            if isinstance(label, dict) and label.get('filter') == 'brend':
                return label.get('title', '')

        # Try from name
        name = data.get('name', '')
        if name:
            # Common patterns
            brand_match = re.match(r'^([A-Za-zА-Яа-я\s]+?)(?:\s+\d+|\s+пиво|\s+вино)', name, re.IGNORECASE)
            if brand_match:
                return brand_match.group(1).strip()

        return ''

    def _extract_section(self, data: Dict) -> List[str]:
        """Extract category hierarchy"""

        section = []

        category = data.get('category', {})
        if isinstance(category, dict):
            # Parent category
            parent = category.get('parent', {})
            if isinstance(parent, dict) and parent.get('name'):
                section.append(parent['name'])

            # Current category
            if category.get('name'):
                section.append(category['name'])

        return section

    def _extract_price_data(self, data: Dict) -> Dict[str, Any]:
        """Extract price information"""

        current = float(data.get('price', 0) or 0)
        original = float(data.get('prev_price') or data.get('price', 0) or 0)

        price_data = {
            'current': current,
            'original': original,
            'sale_tag': ''
        }

        if original > current and original > 0:
            discount = round(((original - current) / original) * 100)
            price_data['sale_tag'] = f"Скидка {discount}%"

        return price_data

    def _extract_stock(self, data: Dict) -> Dict[str, Any]:
        """Extract stock information"""

        return {
            'in_stock': bool(data.get('available', False)),
            'count': int(data.get('quantity', 0) or data.get('quantity_total', 0) or 0)
        }

    def _extract_assets(self, data: Dict) -> Dict[str, Any]:
        """Extract media assets"""

        main_image = data.get('image_url', '')

        return {
            'main_image': main_image,
            'set_images': [main_image] if main_image else [],
            'view360': [],
            'video': []
        }

    def _extract_basic_metadata(self, data: Dict) -> Dict[str, str]:
        """Extract basic metadata from list data"""

        metadata = {}

        metadata['__description'] = data.get('subname', '')

        if data.get('vendor_code'):
            metadata['Артикул'] = str(data['vendor_code'])

        if data.get('uuid'):
            metadata['UUID'] = data['uuid']

        if data.get('quantity_total'):
            metadata['Общее количество'] = str(data['quantity_total'])

        # From filter_labels
        for label in data.get('filter_labels', []):
            if not isinstance(label, dict):
                continue

            filter_type = label.get('filter', '')
            title = label.get('title', '')

            if filter_type == 'strana' and title:
                metadata['Страна'] = title
            elif filter_type == 'obem' and title:
                metadata['Объем'] = title

        return metadata

    def _count_variants(self, data: Dict) -> int:
        """Count product variants (volumes/sizes)"""

        # Try to find volume variations
        volumes = set()

        for block in data.get('description_blocks', []):
            if block.get('code') == 'obem':
                # If there's a range, it might indicate variants
                min_val = block.get('min')
                max_val = block.get('max')
                if min_val != max_val and max_val is not None:
                    return 2  # At least 2 variants
                elif min_val is not None:
                    volumes.add(min_val)

        return len(volumes) if len(volumes) > 1 else 0

    def handle_error(self, failure):
        """Handle request failures"""

        request = failure.request
        self.logger.error(f"Request failed: {failure.value} for URL: {request.url}")

        # Retry logic for specific errors
        if hasattr(failure.value, 'response'):
            response = failure.value.response
            if response and response.status in [403, 429, 503]:
                retry_count = request.meta.get('retry_count', 0)
                if retry_count < 3:
                    self.logger.info(f"Retrying failed request (attempt {retry_count + 1})")
                    new_request = request.copy()
                    new_request.meta['retry_count'] = retry_count + 1
                    new_request.dont_filter = True
                    yield new_request

    def closed(self, reason):
        """Called when spider closes"""

        elapsed = time.time() - self.start_time
        self.logger.info(
            f"Spider closed: {reason}. "
            f"Parsed {self.products_count} products in {elapsed:.1f} seconds. "
            f"Cities discovered: {len(self.cities_found)}"
        )