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

    # --- Specification fields ---
    specs_json = scrapy.Field()  # raw parsed key/value map
    raw_spec_html = scrapy.Field()
    extraction_confidence = scrapy.Field()  # 0.0 - 1.0

    # Pricing: only keep canonical `price` (discount fields removed)

    # Typed spec fields (deprecated - we keep for compatibility but no longer persist)
    spec_battery_mAh = scrapy.Field()
    spec_ram_gb = scrapy.Field()
    spec_storage_gb = scrapy.Field()
    spec_display_in = scrapy.Field()
    spec_display_resolution = scrapy.Field()
    spec_primary_camera_mp = scrapy.Field()
    spec_weight_g = scrapy.Field()
    spec_dimensions_mm = scrapy.Field()  # {height, width, depth}
    spec_sensors = scrapy.Field()
    spec_warranty = scrapy.Field()
