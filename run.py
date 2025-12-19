import yaml
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from tortoise.spiders.flipkart_search_spider import FlipkartSearchSpider


def main():
    # Load crawl config
    with open("config/flipkart.yaml", "r") as f:
        cfg = yaml.safe_load(f)

    # Load Scrapy settings properly
    settings = get_project_settings()

    process = CrawlerProcess(settings)

    for query in cfg["queries"]:
        process.crawl(
            FlipkartSearchSpider,
            query=query,
            max_pages=cfg["max_pages"],
        )

    process.start()


if __name__ == "__main__":
    main()
