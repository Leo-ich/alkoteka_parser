# Alkoteka Parser
Основанный на Scrapy парсер для сбора информации о товарах с alkoteka.com.

## Возможности
- Выбор целевого региона путём указания названия города в настройках
- Полный сбор информации о товарах
- Быстрый сбор информации без посещения карточек товаров
- Поддержка прокси
- Поддержка кеширования

## Установка
### Из GitHub
```
pip install git+https://github.com/Leo-ich/alkoteka_parser.git
```

## Использование
### Как Scrapy project
```
cd alkoteka_parser
scrapy crawl alkoteka -O result.json
```
### С пользовательскими настройками
```
scrapy crawl alkoteka -s TARGET_CITY_NAME="Сочи" -O result_sochi.json
```

### Быстрый сбор информации о товарах
```
scrapy crawl alkoteka -s PARSE_PRODUCT_DETAILS=False -O result_fast.json
```

## Конфигурация
### Выбор категории товаров
Отредактируйте categories.txt для выбора какую категорию парсить:
```
https://alkoteka.com/catalog/slaboalkogolnye-napitki-2
https://alkoteka.com/catalog/vino
https://alkoteka.com/catalog/krepkiy-alkogol
```