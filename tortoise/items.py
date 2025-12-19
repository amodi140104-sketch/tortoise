import scrapy


class FlipkartProductItem(scrapy.Item):
    product_id = scrapy.Field()     # data-id (PRIMARY KEY)
    title = scrapy.Field()
    price = scrapy.Field()
    rating = scrapy.Field()
    product_url = scrapy.Field()
    category = scrapy.Field()
    page = scrapy.Field()
    scraped_at = scrapy.Field()
