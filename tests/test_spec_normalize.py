from tortoise.utils.jsonld import normalize_spec_fields


def test_normalize_from_keys():
    specs = {
        "Battery Capacity": "6000 mAh",
        "RAM": "8 GB",
        "Internal Storage": "128 GB",
        "Display Size": "6.67 inch",
        "Resolution": "1604 x 720 Pixels",
        "Primary Camera": "32MP Rear Camera",
        "Weight": "197 g",
        "Height": "165.7 mm",
        "Width": "76.22 mm",
        "Depth": "7.94 mm",
        "Sensors": "Proximity Sensor, Light Sensor, Geomagnetic Sensor",
        "Warranty Summary": "1 Year Manufacturer Warranty"
    }

    typed = normalize_spec_fields(specs)

    assert typed["spec_battery_mAh"] == 6000
    assert typed["spec_ram_gb"] == 8.0
    assert typed["spec_storage_gb"] == 128.0
    assert abs(typed["spec_display_in"] - 6.67) < 0.01
    assert typed["spec_display_resolution"] == "1604x720"
    assert typed["spec_primary_camera_mp"] == 32.0
    assert typed["spec_weight_g"] == 197.0
    assert typed["spec_dimensions_mm"]["height_mm"] == 165.7
    assert typed["spec_sensors"] == ["Proximity Sensor", "Light Sensor", "Geomagnetic Sensor"]
    assert "warranty" in typed["spec_warranty"].lower()


def test_prevent_blob_contamination():
    # camera spec contains '1/1.57 inch' which should NOT be parsed as display size
    specs = {
        "Primary Camera Features": "50MP Wide Angle (1/1.57 inch sensor)",
        "Sensors": "Magnetic Sensor, Gyroscope",
        "Audio Formats": "MP3, AAC, WAV",
    }

    typed = normalize_spec_fields(specs, raw_html=None)

    # display size should NOT be set from camera "1/1.57"
    assert "spec_display_in" not in typed
    # sensors should only contain the two sensors
    assert typed["spec_sensors"] == ["Magnetic Sensor", "Gyroscope"]


if __name__ == "__main__":
    test_normalize_from_keys()
    test_prevent_blob_contamination()
    print("tests passed")