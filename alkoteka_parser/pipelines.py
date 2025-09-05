# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

"""
Item pipelines for data validation and cleaning
"""

import logging
from typing import Any, Dict


class ValidationPipeline:
    """Validate and ensure all required fields are present"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.processed_count = 0
        self.error_count = 0

    def process_item(self, item, spider):
        self.processed_count += 1

        # Define required fields with their default values
        required_fields = {
            'timestamp': 0,
            'RPC': '',
            'url': '',
            'title': '',
            'marketing_tags': [],
            'brand': '',
            'section': [],
            'price_data': {
                'current': 0.0,
                'original': 0.0,
                'sale_tag': ''
            },
            'stock': {
                'in_stock': False,
                'count': 0
            },
            'assets': {
                'main_image': '',
                'set_images': [],
                'view360': [],
                'video': []
            },
            'metadata': {
                '__description': ''
            },
            'variants': 0
        }

        # Check and set defaults for missing fields
        for field, default in required_fields.items():
            if field not in item:
                self.logger.debug(f"Missing field '{field}' in item, setting default")
                item[field] = default
                self.error_count += 1

        # Validate specific field types
        self._validate_types(item)

        # Log statistics periodically
        if self.processed_count % 100 == 0:
            self.logger.info(
                f"Processed {self.processed_count} items, "
                f"fixed {self.error_count} missing fields"
            )

        return item

    def _validate_types(self, item):
        """Ensure correct data types"""

        # Lists
        for field in ['marketing_tags', 'section']:
            if not isinstance(item.get(field), list):
                item[field] = []

        # Dictionaries
        for field in ['price_data', 'stock', 'assets', 'metadata']:
            if not isinstance(item.get(field), dict):
                item[field] = {}

        # Ensure assets sub-fields are lists
        if 'assets' in item:
            for subfield in ['set_images', 'view360', 'video']:
                if subfield not in item['assets']:
                    item['assets'][subfield] = []
                elif not isinstance(item['assets'][subfield], list):
                    item['assets'][subfield] = []

        # Ensure price_data has required fields
        if 'price_data' in item:
            for field in ['current', 'original']:
                if field not in item['price_data']:
                    item['price_data'][field] = 0.0
            if 'sale_tag' not in item['price_data']:
                item['price_data']['sale_tag'] = ''

        # Ensure stock has required fields
        if 'stock' in item:
            if 'in_stock' not in item['stock']:
                item['stock']['in_stock'] = False
            if 'count' not in item['stock']:
                item['stock']['count'] = 0


class DataCleaningPipeline:
    """Clean and normalize data"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def process_item(self, item, spider):
        # Clean string fields
        string_fields = ['RPC', 'url', 'title', 'brand']
        for field in string_fields:
            if field in item and item[field]:
                item[field] = str(item[field]).strip()

        # Remove duplicate tags
        if 'marketing_tags' in item:
            item['marketing_tags'] = list(dict.fromkeys(item['marketing_tags']))

        # Remove duplicate images
        if 'assets' in item and 'set_images' in item['assets']:
            item['assets']['set_images'] = list(dict.fromkeys(item['assets']['set_images']))

        # Ensure numeric types
        if 'price_data' in item:
            for field in ['current', 'original']:
                if field in item['price_data']:
                    try:
                        item['price_data'][field] = float(item['price_data'][field])
                    except (TypeError, ValueError):
                        item['price_data'][field] = 0.0

        if 'stock' in item and 'count' in item['stock']:
            try:
                item['stock']['count'] = int(item['stock']['count'])
            except (TypeError, ValueError):
                item['stock']['count'] = 0

        if 'variants' in item:
            try:
                item['variants'] = int(item['variants'])
            except (TypeError, ValueError):
                item['variants'] = 0

        # Clean metadata - remove None values
        if 'metadata' in item:
            item['metadata'] = {
                k: v for k, v in item['metadata'].items()
                if v is not None
            }

        return item

    def close_spider(self, spider):
        """Log final statistics"""

        spider.logger.info(f"Pipeline finished processing {spider.products_count} products")


class AlkotekaPipeline:
    def process_item(self, item, spider):      
        return item
