from tortoise.utils.jsonld import compute_spec_confidence


def test_confidence_all_present():
    specs = {
        "Battery Capacity": "6000 mAh",
        "RAM": "8 GB",
        "Internal Storage": "128 GB",
        "Display Size": "6.67 inch",
        "Primary Camera": "32MP",
        "Weight": "190 g",
    }
    assert compute_spec_confidence(specs) == 1.0


def test_confidence_partial():
    specs = {"Battery Capacity": "5000 mAh", "RAM": "4 GB"}
    assert compute_spec_confidence(specs) == 0.33


def test_confidence_none():
    assert compute_spec_confidence({}) == 0.0


if __name__ == '__main__':
    test_confidence_all_present()
    test_confidence_partial()
    test_confidence_none()
    print('confidence tests passed')