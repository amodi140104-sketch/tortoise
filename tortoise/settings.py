BOT_NAME = "tortoise"

SPIDER_MODULES = ["tortoise.spiders"]
NEWSPIDER_MODULE = "tortoise.spiders"

# ROBOTSTXT_OBEY = True

ROBOTSTXT_OBEY = False

DOWNLOAD_DELAY = 4.5
RANDOMIZE_DOWNLOAD_DELAY = True
CONCURRENT_REQUESTS = 1

AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 3
AUTOTHROTTLE_MAX_DELAY = 15

# Flush feed exporter after every item so output files (e.g. JSON lines) are written incrementally.
# This reduces the perceived delay when using `-O` (json array) or `-o` (jsonlines) during long runs.
FEED_EXPORT_ENCODING = "utf-8"
FEED_EXPORT_BATCH_ITEM_COUNT = 1

# Tunable settings to reduce IO and speed crawls
# Number of DB inserts to batch before committing (larger -> fewer commits)
DB_COMMIT_EVERY = 10
# Number of items between JSON-array file rewrites (1 means rewrite every item)
JSON_ARRAY_WRITE_EVERY = 5
# DB file path used by pipeline/storage
DB_PATH = "data/flipkart.db"

# Path used by the incremental JSON array writer pipeline below
JSON_ARRAY_FILE = "mobiles.json"

ITEM_PIPELINES = {
    "tortoise.pipelines.FlipkartPipeline": 300,
    "tortoise.pipelines.JsonArrayPipeline": 400,
}


DOWNLOADER_MIDDLEWARES = {
    "tortoise.middlewares.RandomUserAgentMiddleware": 400,
    "tortoise.middlewares.FlipkartRetryMiddleware": 550,
}
