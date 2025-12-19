# from scrapy.exceptions import DropItem


# class FlipkartPipeline:
#     def __init__(self):
#         self.seen_ids = set()

#     def process_item(self, item, spider):
#         pid = item["product_id"]

#         if pid in self.seen_ids:
#             raise DropItem(f"Duplicate product {pid}")

#         self.seen_ids.add(pid)
#         return item


from scrapy.exceptions import DropItem
from tortoise.storage import Storage


class FlipkartPipeline:
    def __init__(self, storage):
        self.seen_ids = set()
        self.storage = storage

    @classmethod
    def from_crawler(cls, crawler):
        commit_every = crawler.settings.getint("DB_COMMIT_EVERY", 10)
        db_path = crawler.settings.get("DB_PATH", "data/flipkart.db")
        storage = Storage(db_path, commit_every=commit_every)
        pipeline = cls(storage)
        # Ensure storage pending commits are flushed on spider close
        from scrapy import signals
        crawler.signals.connect(lambda spider: storage.commit_pending(), signals.spider_closed)
        return pipeline

    def process_item(self, item, spider):
        # Be defensive: some items may miss `product_id` which previously caused KeyError and
        # prevented the feed exporter from writing the item. Log and drop those.
        pid = item.get("product_id")
        if not pid:
            spider.logger.warning(f"Missing product_id, skipping item: {dict(item)}")
            raise DropItem("Missing product_id")

        if pid in self.seen_ids:
            raise DropItem(f"Duplicate product {pid}")

        self.seen_ids.add(pid)

        # Persist item; if DB write fails, log and continue so the feed exporter still gets the item
        try:
            self.storage.save_item(item)
        except Exception as exc:
            spider.logger.error(f"Failed to persist item {pid}: {exc}")

        return item


# --- JsonArrayPipeline modifications: write every N items instead of every item ---
class JsonArrayPipeline:
    """Write a valid JSON array to disk and overwrite it periodically.

    The frequency is controlled by `JSON_ARRAY_WRITE_EVERY` (default 1). For faster
    runs set it to a higher value (e.g., 5 or 10) so the file is not rewritten on
    every single item.
    """

    def __init__(self, file_path="mobiles.json"):
        from pathlib import Path
        self.file_path = Path(file_path)
        self.items_by_id = {}
        self._item_count = 0
        self.write_every = 1

    @classmethod
    def from_crawler(cls, crawler):
        file_path = crawler.settings.get("JSON_ARRAY_FILE", "mobiles.json")
        pipeline = cls(file_path)
        pipeline.write_every = crawler.settings.getint("JSON_ARRAY_WRITE_EVERY", 1)
        from scrapy import signals
        crawler.signals.connect(pipeline.spider_opened, signals.spider_opened)
        crawler.signals.connect(pipeline.spider_closed, signals.spider_closed)
        return pipeline

    def spider_opened(self, spider):
        # Load any existing file to keep historic items
        import json
        try:
            if self.file_path.exists():
                with self.file_path.open("r", encoding="utf-8") as fh:
                    data = json.load(fh)
                    for itm in data:
                        pid = itm.get("product_id")
                        if pid:
                            self.items_by_id[pid] = itm
        except Exception:
            spider.logger.exception("Failed to load existing JSON array file; starting fresh.")

    def process_item(self, item, spider):
        pid = item.get("product_id")
        if not pid:
            # Skip items without id (FlipkartPipeline already drops them, but be safe)
            return item

        # Update the in-memory map and rewrite file periodically
        self.items_by_id[pid] = dict(item)
        self._item_count += 1
        if self.write_every <= 1 or (self._item_count % self.write_every) == 0:
            self._write_file()
        return item

    def _write_file(self):
        import json
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        with self.file_path.open("w", encoding="utf-8") as fh:
            json.dump(list(self.items_by_id.values()), fh, ensure_ascii=False, indent=2)

    def spider_closed(self, spider):
        # Ensure final write
        self._write_file()


class JsonArrayPipeline:
    """Write a valid JSON array to disk and overwrite it after every item.

    This makes `mobiles.json` a valid, readable JSON array even while the spider
    is running. For small limits (e.g., 150 items) overwriting the file on each
    item is efficient and simple.
    """

    def __init__(self, file_path="mobiles.json"):
        from pathlib import Path
        self.file_path = Path(file_path)
        self.items_by_id = {}

    @classmethod
    def from_crawler(cls, crawler):
        file_path = crawler.settings.get("JSON_ARRAY_FILE", "mobiles.json")
        pipeline = cls(file_path)
        from scrapy import signals
        crawler.signals.connect(pipeline.spider_opened, signals.spider_opened)
        crawler.signals.connect(pipeline.spider_closed, signals.spider_closed)
        return pipeline

    def spider_opened(self, spider):
        # Load any existing file to keep historic items
        import json
        try:
            if self.file_path.exists():
                with self.file_path.open("r", encoding="utf-8") as fh:
                    data = json.load(fh)
                    for itm in data:
                        pid = itm.get("product_id")
                        if pid:
                            self.items_by_id[pid] = itm
        except Exception:
            spider.logger.exception("Failed to load existing JSON array file; starting fresh.")

    def process_item(self, item, spider):
        pid = item.get("product_id")
        if not pid:
            # Skip items without id (FlipkartPipeline already drops them, but be safe)
            return item

        # Update the in-memory map and rewrite file
        self.items_by_id[pid] = dict(item)
        self._write_file()
        return item

    def _write_file(self):
        import json
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        with self.file_path.open("w", encoding="utf-8") as fh:
            json.dump(list(self.items_by_id.values()), fh, ensure_ascii=False, indent=2)

    def spider_closed(self, spider):
        # Ensure final write
        self._write_file()
