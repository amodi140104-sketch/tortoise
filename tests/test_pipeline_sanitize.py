from tortoise.pipelines import JsonArrayPipeline


def test_jsonarray_pipeline_sanitizes():
    pipeline = JsonArrayPipeline(file_path='test_mobiles.json')
    # construct item with extra keys
    item = {
        'product_id': 'PID123',
        'title': 'Sample',
        'product_url': 'https://example.com/p/1',
        'price': 100,
        'rating': 4.2,
        'category': 'mobiles',
        'page': 1,
        'scraped_at': '2025-01-01T00:00:00Z',
        'specs_json': {'Battery Capacity': '6000 mAh'},
        'spec_battery_mAh': 6000,
        'raw_spec_html': '<table>..</table>',
        'extraction_confidence': 1.0,
        'extra': 'should be removed'
    }

    pipeline.spider_opened(None)
    pipeline.process_item(item, spider=None)
    stored = pipeline.items_by_id.get('PID123')

    assert 'spec_battery_mAh' not in stored
    assert 'raw_spec_html' not in stored
    assert 'extraction_confidence' not in stored
    assert 'extra' not in stored

    # allowed fields present
    for k in ['product_id','title','product_url','price','rating','category','page','scraped_at','specs_json']:
        assert k in stored


def test_invalid_price_cleared():
    pipeline = JsonArrayPipeline(file_path='test_mobiles.json')
    item = {
        'product_id': 'PID400',
        'price': 25999,
        'price_discount': 25999,
        'price_original': 40000,
        'price_discount_pct': 35.0,
    }
    pipeline.spider_opened(None)
    pipeline.process_item(item, spider=None)
    stored = pipeline.items_by_id.get('PID400')
    assert stored['price'] == 25999
    # discount-related fields should be removed entirely
    assert 'price_discount' not in stored
    assert 'price_original' not in stored
    assert 'price_discount_pct' not in stored


if __name__ == '__main__':
    test_jsonarray_pipeline_sanitizes()
    test_invalid_price_cleared()
    print('pipeline sanitize test passed')

if __name__ == '__main__':
    test_jsonarray_pipeline_sanitizes()
    print('pipeline sanitize test passed')