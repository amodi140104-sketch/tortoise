from parsel import Selector
from tortoise.utils.jsonld import extract_price_info


def make_response(html):
    # parsel.Selector has .xpath similar to Scrapy response
    return Selector(text=html)


def test_price_with_strike_and_jsonld():
    html = '<div><strike>₹ 19,999</strike><span class="_30jeq3">₹ 13,999</span></div>'
    resp = make_response(html)
    info = extract_price_info(resp, price_from_jsonld=13999)
    assert info['original_price'] == 19999
    assert info['discounted_price'] == 13999
    assert round(info['discount_pct'], 1) == round((19999-13999)/19999*100, 1)


def test_price_only_jsonld():
    html = '<div><span class="_30jeq3">₹ 13,999</span></div>'
    resp = make_response(html)
    info = extract_price_info(resp, price_from_jsonld=13999)
    assert info['original_price'] is None
    assert info['discounted_price'] == 13999
    assert info['discount_pct'] is None


def test_price_from_page_when_no_jsonld():
    html = '<div><strike>₹ 20,000</strike><span class="price">₹ 15,000</span></div>'
    resp = make_response(html)
    info = extract_price_info(resp, price_from_jsonld=None)
    assert info['original_price'] == 20000
    assert info['discounted_price'] == 15000
    assert round(info['discount_pct'], 2) == 25.0


def test_price_ignores_unrelated_large_amounts():
    html = ('<div class="price-block"><strike>₹ 29,999</strike>'
            '<span class="_30jeq3">₹ 25,999</span></div>'
            '<div class="other-info">EMI starts from ₹ 40,000</div>')
    resp = make_response(html)
    info = extract_price_info(resp, price_from_jsonld=None)
    # original should be the nearby strike (29999) not the unrelated 40000
    assert info['original_price'] == 29999
    assert info['discounted_price'] == 25999
    assert round(info['discount_pct'], 2) == round((29999-25999)/29999*100, 2)


if __name__ == '__main__':
    test_price_with_strike_and_jsonld()
    test_price_only_jsonld()
    test_price_from_page_when_no_jsonld()
    test_price_ignores_unrelated_large_amounts()
    print('price tests passed')