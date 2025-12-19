import json

def extract_products_from_jsonld(response):
    """
    Returns a list of Product dicts from all JSON-LD blocks.
    Works for both search & product pages.
    """
    products = []

    scripts = response.xpath(
        '//script[@type="application/ld+json"]/text()'
    ).getall()

    for script in scripts:
        try:
            data = json.loads(script)
        except json.JSONDecodeError:
            continue

        _walk_json(data, products)

    return products


def _walk_json(node, products):
    if isinstance(node, dict):
        if node.get("@type") == "Product":
            products.append(node)

        for v in node.values():
            _walk_json(v, products)

    elif isinstance(node, list):
        for item in node:
            _walk_json(item, products)
