import json

def parse_product(self, response):
    item = response.meta["item"]

    pid = response.url.split("pid=")[1].split("&")[0]
    if pid != item["product_id"]:
        return

    json_text = response.css("script#__NEXT_DATA__::text").get()
    if not json_text:
        yield item
        return

    data = json.loads(json_text)

    # Navigate JSON safely
    try:
        product = (
            data["props"]["pageProps"]["initialState"]["productPage"]["productDetails"]["value"]
        )
    except KeyError:
        yield item
        return

    # Fill missing fields
    if not item["title"]:
        item["title"] = product.get("titles", {}).get("title")

    if not item["price"]:
        item["price"] = product.get("pricing", {}).get("finalPrice", {}).get("value")

    if not item["rating"]:
        item["rating"] = product.get("rating", {}).get("average")

    yield item
