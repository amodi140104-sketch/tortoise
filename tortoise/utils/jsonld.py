import json
import re


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


# -----------------------------
# Specification extraction
# -----------------------------

def extract_specifications(response):
    """
    Heuristic extraction of product specifications from the product page HTML.
    Returns (specs_dict, raw_html)
    - specs_dict: mapping of key -> value (strings)
    - raw_html: HTML snippet extracted (or None)

    Strategy:
    1. Look for headings containing "spec" and parse following sibling block
    2. Fallback to parsing any tables on the page
    3. Fallback to parsing list items (li) with "key: value"
    """
    # 1) look for headings
    heading_sel = response.xpath(
        "//h2|//h3|//h4|//h5|//h1"
    )
    for h in heading_sel:
        text = " ".join(h.xpath('.//text()').getall()).strip().lower()
        if "spec" in text or "key specs" in text or "product details" in text or "product information" in text:
            # take the next few sibling elements as spec section
            section_nodes = h.xpath("following-sibling::*[position() <= 6]")
            specs = _parse_section_nodes(section_nodes)
            if specs:
                raw_html = "".join([s.get() for s in section_nodes])
                return specs, raw_html

    # 2) parse all table rows
    specs = {}
    rows = response.xpath("//table//tr")
    if rows:
        for tr in rows:
            parts = [p.strip() for p in tr.xpath('.//th//text() | .//td//text()').getall() if p.strip()]
            if len(parts) >= 2:
                key = parts[0]
                value = " ".join(parts[1:])
                specs[key] = value
        if specs:
            raw_html = "".join([t.get() for t in response.xpath("//table")])
            return specs, raw_html

    # 3) li items with colon
    for li in response.xpath("//li"):
        text = " ".join(li.xpath('.//text()').getall()).strip()
        if text and ":" in text:
            k, v = text.split(":", 1)
            specs[k.strip()] = v.strip()

    raw_html = None
    return specs, raw_html


def _parse_section_nodes(section_nodes):
    specs = {}

    # look for tables inside section
    rows = section_nodes.xpath('.//tr')
    if rows:
        for tr in rows:
            parts = [p.strip() for p in tr.xpath('.//th//text() | .//td//text()').getall() if p.strip()]
            if len(parts) >= 2:
                key = parts[0]
                value = " ".join(parts[1:])
                specs[key] = value
        if specs:
            return specs

    # look for lists
    lis = section_nodes.xpath('.//li')
    for li in lis:
        text = " ".join(li.xpath('.//text()').getall()).strip()
        if text and ":" in text:
            k, v = text.split(":", 1)
            specs[k.strip()] = v.strip()
    if specs:
        return specs

    # generic rows: pairs of adjacent div/text lines
    # try to find elements with two child nodes carrying texts
    pairs = section_nodes.xpath('.//div[count(.//text())>0]')
    for node in pairs:
        texts = [t.strip() for t in node.xpath('.//text()').getall() if t.strip()]
        # heuristics: if exactly 2 text parts treat as key/value
        if len(texts) == 2:
            specs[texts[0]] = texts[1]

    return specs


# -----------------------------
# Normalization helpers
# -----------------------------

def normalize_spec_fields(specs, raw_html=None):
    """
    Prefer key-based parsing from `specs` dict. Fallback to the global text blob only
    when keys are missing. Returns typed fields + `extraction_confidence`.
    """

    typed = {}

    # canonical key map: map candidate keys to our typed fields
    key_map = {
        "spec_battery_mAh": ["battery capacity", "battery", "battery & power features"],
        "spec_ram_gb": ["ram", "ram (gb)", "memory"],
        "spec_storage_gb": ["internal storage", "storage", "rom"],
        "spec_display_in": ["display size", "screen size"],
        "spec_display_resolution": ["resolution", "display resolution"],
        "spec_primary_camera_mp": ["primary camera", "rear camera", "primary camera mp"],
        "spec_weight_g": ["weight"],
        "spec_dimensions_mm": ["height", "width", "depth", "dimensions"],
        "spec_sensors": ["sensors"],
        "spec_warranty": ["warranty", "warranty summary", "warranty period"]
    }

    def _find_value_for_keys(candidates):
        for k in candidates:
            for key, val in specs.items():
                if key and k in key.lower():
                    return val
        return None

    def _extract_number(text, regex):
        m = re.search(regex, text, re.I)
        return m.group(1) if m else None

    # Use direct keys first
    # 1) battery
    battery_val = _find_value_for_keys(key_map["spec_battery_mAh"]) or ""
    m = _extract_number(str(battery_val), r"(\d{3,5})\s*mAh")
    if m:
        typed["spec_battery_mAh"] = int(m)

    # 2) RAM (prefer explicit RAM key; fall back to 'RAM' inside 'Internal Storage' or generic)
    ram_val = _find_value_for_keys(key_map["spec_ram_gb"]) or specs.get("RAM") or ""
    m = _extract_number(str(ram_val), r"(\d+(?:\.\d+)?)\s*GB")
    if m:
        typed["spec_ram_gb"] = float(m)

    # 3) storage
    storage_val = _find_value_for_keys(key_map["spec_storage_gb"]) or specs.get("Internal Storage") or ""
    m = _extract_number(str(storage_val), r"(\d+(?:\.\d+)?)\s*GB")
    if m:
        typed["spec_storage_gb"] = float(m)

    # 4) display size (prefer specific key)
    disp_val = _find_value_for_keys(key_map["spec_display_in"]) or specs.get("Display Size") or ""
    # look for inch first
    m = _extract_number(str(disp_val), r"(\d+(?:\.\d+)?)\s*(?:inch|inches)")
    if m:
        typed["spec_display_in"] = float(m)
    else:
        # fallback to cm
        m = _extract_number(str(disp_val), r"(\d+(?:\.\d+)?)\s*cm")
        if m:
            try:
                typed["spec_display_in"] = round(float(m) / 2.54, 2)
            except Exception:
                pass

    # 5) resolution
    res_val = _find_value_for_keys(key_map["spec_display_resolution"]) or specs.get("Resolution") or ""
    if res_val:
        m = re.search(r"(\d+\s*[x×]\s*\d+)", str(res_val), re.I)
        if m:
            typed["spec_display_resolution"] = re.sub(r"\s+", "", m.group(1))

    # 6) primary camera
    cam_val = _find_value_for_keys(key_map["spec_primary_camera_mp"]) or specs.get("Primary Camera") or ""
    if cam_val:
        m = re.search(r"(\d+(?:\.\d+)?)\s*MP", str(cam_val), re.I)
        if m:
            typed["spec_primary_camera_mp"] = float(m.group(1))

    # 7) weight
    weight_val = _find_value_for_keys(key_map["spec_weight_g"]) or specs.get("Weight") or ""
    if weight_val:
        m = re.search(r"(\d+(?:\.\d+)?)\s*g\b", str(weight_val), re.I)
        if m:
            typed["spec_weight_g"] = float(m.group(1))

    # 8) dimensions
    # prefer explicit H, W, D keys
    dims = {}
    for d_key in ["Height", "Width", "Depth"]:
        if d_key in specs:
            v = _extract_number(str(specs[d_key]), r"([\d\.]+)\s*mm")
            if v:
                dims[d_key.lower() + "_mm"] = float(v)
    if dims:
        typed["spec_dimensions_mm"] = dims
    else:
        # fallback to 'Dimensions' or look for 'HxWxD mm' in the blob
        dim_val = specs.get("Dimensions") or ""
        if dim_val:
            m = re.search(r"(\d+(?:\.\d+)?)\s*[x×]\s*(\d+(?:\.\d+)?)\s*[x×]\s*(\d+(?:\.\d+)?)\s*mm", str(dim_val), re.I)
            if m:
                typed["spec_dimensions_mm"] = {
                    "height_mm": float(m.group(1)),
                    "width_mm": float(m.group(2)),
                    "depth_mm": float(m.group(3)),
                }

    # 9) sensors: strictly from Sensors key
    sensors_val = _find_value_for_keys(key_map["spec_sensors"]) or specs.get("Sensors") or ""
    if sensors_val:
        # split on commas/semicolons and clean up obvious trailing garbage
        parts = [p.strip() for p in re.split(r",|;", str(sensors_val)) if p.strip()]
        # keep only short tokens (avoid huge blocks coming from other fields), drop tokens that contain many words (>8)
        clean = [p for p in parts if len(p.split()) <= 8]
        typed["spec_sensors"] = clean

    # 10) warranty
    w_val = _find_value_for_keys(key_map["spec_warranty"]) or specs.get("Warranty Summary") or specs.get("Warranty") or ""
    if w_val:
        typed["spec_warranty"] = str(w_val).strip()

    # If some fields are missing, fallback to scanning the full text blob but keep them as lower-confidence
    missing_main = [k for k in ["spec_battery_mAh", "spec_ram_gb", "spec_storage_gb", "spec_display_in", "spec_primary_camera_mp", "spec_weight_g"] if k not in typed]
    if missing_main and specs:
        text_blob = " ".join([f"{k} {v}" for k, v in specs.items()]) if specs else (raw_html or "")
        # conservative regex matches only when we don't have the key
        if "spec_battery_mAh" in missing_main:
            m = re.search(r"(\d{3,5})\s*mAh", text_blob, re.I)
            if m:
                typed["spec_battery_mAh"] = int(m.group(1))
        if "spec_ram_gb" in missing_main:
            m = re.search(r"\b(\d+(?:\.\d+)?)\s*GB\b", text_blob, re.I)
            if m:
                typed["spec_ram_gb"] = float(m.group(1))
        if "spec_storage_gb" in missing_main:
            m = re.search(r"\b(\d+(?:\.\d+)?)\s*GB\b", text_blob, re.I)
            if m:
                typed.setdefault("spec_storage_gb", float(m.group(1)))
        if "spec_display_in" in missing_main:
            # Be conservative: only accept a fallback display size if the match is
            # found near a 'display' or 'screen' context to avoid camera-sensor matches
            m = re.search(r"(?:display|screen)[^\n]{0,80}?(\d+(?:\.\d+)?)\s*(?:inch|inches)\b", text_blob, re.I)
            if m:
                typed["spec_display_in"] = float(m.group(1))
            else:
                m = re.search(r"(?:display|screen)[^\n]{0,80}?(\d+(?:\.\d+)?)\s*cm\b", text_blob, re.I)
                if m:
                    try:
                        typed["spec_display_in"] = round(float(m.group(1)) / 2.54, 2)
                    except Exception:
                        pass
        if "spec_primary_camera_mp" in missing_main:
            m = re.search(r"(\d+(?:\.\d+)?)\s*MP", text_blob, re.I)
            if m:
                typed["spec_primary_camera_mp"] = float(m.group(1))
        if "spec_weight_g" in missing_main:
            m = re.search(r"(\d+(?:\.\d+)?)\s*g\b", text_blob, re.I)
            if m:
                typed["spec_weight_g"] = float(m.group(1))

    # Compute confidence: higher weight if parsed from explicit keys
    main_keys = ["spec_battery_mAh", "spec_ram_gb", "spec_storage_gb", "spec_display_in", "spec_primary_camera_mp", "spec_weight_g"]
    hits = sum(2 if k in specs and k.replace("spec_", "").replace("_", " ").title() in specs else 1 for k in main_keys if k in typed)
    max_score = 2 * len(main_keys)
    confidence = min(1.0, hits / max_score)

    typed["extraction_confidence"] = round(confidence, 2)

    return typed


# -----------------------------
# Spec confidence helper
# -----------------------------

def compute_spec_confidence(specs, core_keys=None):
    """
    Compute a conservative confidence score (0.0-1.0) based on the presence of
    core specification keys in the `specs` dict.
    """
    if not specs:
        return 0.0
    core = core_keys or ["Battery Capacity", "RAM", "Internal Storage", "Display Size", "Primary Camera", "Weight"]
    hits = sum(1 for k in core if any(k.lower() == s_key.lower() for s_key in specs.keys()))
    return round(hits / len(core), 2)


# -----------------------------
# Price extraction
# -----------------------------

def extract_price_info(response, price_from_jsonld=None):
    """
    Heuristic extraction of price information from the product page HTML.
    Returns a dict: {original_price, discounted_price, discount_pct}
    - Uses jsonld price as primary discounted_price if provided
    - Scans page for rupee amounts and strike elements to find original price
    """
    # Prefer price elements near the main price block (Flipkart uses classes like _30jeq3 for current price)
    def _parse_amount_from_text(txt):
        m = re.search(r"₹\s*([\d,]+)", txt)
        if not m:
            m = re.search(r"([\d,]+)", txt)
        if m:
            try:
                return int(m.group(1).replace(',', ''))
            except Exception:
                return None
        return None

    # 1) attempt to locate discounted price on page (class-based)
    discounted = price_from_jsonld
    discounted_page = None
    disc_nodes = response.xpath('//div[contains(@class,"_30jeq3") or contains(@class,"_16Jk6d") or contains(@class,"_1vC4OE")]')
    if disc_nodes:
        for dn in disc_nodes:
            txt = " ".join(dn.xpath('.//text()').getall()).strip()
            v = _parse_amount_from_text(txt)
            if v:
                discounted_page = v
                break

    if discounted is None and discounted_page is not None:
        discounted = discounted_page

    # 2) try to find original price near the discounted element (within ancestor block)
    original = None
    if disc_nodes:
        for dn in disc_nodes:
            # search within a reasonable ancestor scope for strike/del or original-price class
            ancestor = dn.xpath('ancestor::div[1]') or dn.xpath('ancestor::div[2]')
            texts = []
            for anc in ancestor:
                texts.extend(anc.xpath('.//strike//text() | .//del//text() | .//div[contains(@class,"_3I9_wc")]//text()').getall())
            for t in texts:
                v = _parse_amount_from_text(t)
                if v and (discounted is None or v > discounted):
                    original = v
                    break
            if original:
                break

    # 3) fallback to global scan, but be conservative
    if original is None:
        text_nodes = response.xpath("//text()" ).getall()
        text_blob = "\n".join(text_nodes)

        # find rupee amounts like '₹ 12,345' or numbers 12,345
        amounts = []
        for m in re.finditer(r"₹\s*([\d,]+)", text_blob):
            try:
                amt = int(m.group(1).replace(',', ''))
                amounts.append(amt)
            except Exception:
                continue

        # also look for striked prices in <strike> or <del>
        strike_texts = response.xpath('//strike//text() | //del//text()').getall()
        strikes = []
        for s in strike_texts:
            m = re.search(r"([\d,]+)", s)
            if m:
                strikes.append(int(m.group(1).replace(',', '')))

        # prefer strike values for original
        if strikes:
            # choose the max strike value greater than discounted
            candidates = [s for s in strikes if (discounted is None or s > discounted)]
            if candidates:
                original = max(candidates)

        # otherwise choose largest amount greater than discounted
        if original is None and amounts:
            candidates = [a for a in amounts if (discounted is None or a > discounted)]
            if candidates:
                original = max(candidates)

    discount_pct = None
    if original and discounted:
        try:
            discount_pct = round((original - discounted) / original * 100, 2)
        except Exception:
            discount_pct = None

    return {"original_price": original, "discounted_price": discounted, "discount_pct": discount_pct}
