import re
import scrapy
from urllib.parse import urlencode, urlparse, parse_qs
from datetime import datetime, timezone, timedelta
from scrapy.exceptions import CloseSpider
from tortoise.items import FlipkartProductItem
from tortoise.utils.jsonld import extract_products_from_jsonld


class FlipkartSearchSpider(scrapy.Spider):
    name = "flipkart_search"
    allowed_domains = ["flipkart.com"]

    custom_settings = {
        "CONCURRENT_REQUESTS": 1,
        "DOWNLOAD_DELAY": 4.5,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
        "AUTOTHROTTLE_ENABLED": True,
    }

    def __init__(self, query, max_pages=20, max_items=55, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.query = query
        self.max_pages = int(max_pages)
        self.max_items = int(max_items)
        self.items_scraped = 0
        self.seen_ids = set()

    # ------------------------------------------------------------------
    # START REQUESTS (SEARCH PAGES)
    # ------------------------------------------------------------------
    def start_requests(self):
        for page in range(1, self.max_pages + 1):
            if self.items_scraped >= self.max_items:
                self.logger.info(f"Reached max items ({self.max_items}), stopping crawl.")
                break

            params = {"q": self.query, "page": page}
            url = f"https://www.flipkart.com/search?{urlencode(params)}"

            yield scrapy.Request(
                url=url,
                callback=self.parse_search,
                meta={"page": page},
            )

    # ------------------------------------------------------------------
    # SEARCH PAGE: ONLY EXTRACT LINKS + PID
    # ------------------------------------------------------------------
    def parse_search(self, response):
        page = response.meta["page"]

        cards = response.xpath('//div[@data-id]')
        if not cards:
            self.logger.info(f"No products found on page {page}")
            return

        for card in cards:
            if self.items_scraped >= self.max_items:
                raise CloseSpider('max_items_reached')

            pid = card.attrib.get("data-id")
            href = card.xpath('.//a[@href][1]/@href').get()

            if not pid or not href:
                continue

            if pid in self.seen_ids:
                # already scheduled or processed
                continue

            product_url = response.urljoin(href)

            yield scrapy.Request(
                url=product_url,
                callback=self.parse_product,
                meta={
                    "product_id": pid,
                    "page": page,
                },
            )

    # ------------------------------------------------------------------
    # PRODUCT PAGE: JSON-LD IS THE SOURCE OF TRUTH
    # ------------------------------------------------------------------
    def parse_product(self, response):
        product_id = response.meta["product_id"]
        page = response.meta["page"]

        products = extract_products_from_jsonld(response)

        if not products:
            self.logger.warning(f"No JSON-LD Product found: {response.url}")
            return

        product = products[0]

        # avoid duplicates
        if product_id in self.seen_ids:
            return

        self.seen_ids.add(product_id)
        self.items_scraped += 1

        item = FlipkartProductItem()

        item["product_id"] = product_id
        item["title"] = product.get("name")
        item["product_url"] = product.get("url", response.url)

        # --- PRICE ---
        offers = product.get("offers", {})
        price_raw = offers.get("price")
        price = None
        if price_raw is not None:
            price_text = str(price_raw)
            price_digits = re.sub(r"[^\d.]", "", price_text)
            if price_digits:
                try:
                    price = int(float(price_digits))
                except Exception:
                    price = None
        item["price"] = price

        # --- RATING ---
        rating = product.get("aggregateRating", {})
        rating_value = rating.get("ratingValue")
        try:
            item["rating"] = float(rating_value) if rating_value is not None else None
        except Exception:
            item["rating"] = None

        item["category"] = self.query
        item["page"] = page
        # Convert scraped time to IST (UTC+05:30)
        ist = timezone(timedelta(hours=5, minutes=30))
        item["scraped_at"] = datetime.now(ist).isoformat()

        yield item

        if self.items_scraped >= self.max_items:
            raise CloseSpider('max_items_reached')
