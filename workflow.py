from __future__ import annotations

import json
from urllib.parse import quote_plus, urlparse


DEFAULT_RESULT_SCHEMA = {
    "vendor": None,
    "searched_product": None,
    "matched_product_name": None,
    "matched_url": None,
    "price": None,
    "currency": None,
    "availability": None,
    "shipping_notes": None,
    "return_policy_notes": None,
    "confidence": None,
    "notes": None,
    "captured_at": None,
}


def normalize_vendor_list(raw_value: str) -> list[str]:
    vendors: list[str] = []
    seen: set[str] = set()

    for chunk in raw_value.replace(",", "\n").splitlines():
        cleaned = chunk.strip()
        if not cleaned:
            continue
        if not cleaned.startswith(("http://", "https://")):
            cleaned = "https://" + cleaned
        if cleaned in seen:
            continue
        seen.add(cleaned)
        vendors.append(cleaned)

    return vendors


def vendor_name_from_url(url: str) -> str:
    hostname = urlparse(url).netloc.lower()
    if hostname.startswith("www."):
        hostname = hostname[4:]
    base = hostname.split(".")[0] if hostname else "vendor"
    return base.replace("-", " ").replace("_", " ").title()


def build_entry_url(vendor_url: str, product_query: str) -> str:
    parsed = urlparse(vendor_url)
    hostname = parsed.netloc.lower()
    query = quote_plus(product_query)

    if "bestbuy.com" in hostname:
        return f"https://www.bestbuy.com/site/searchpage.jsp?st={query}"
    if "target.com" in hostname:
        return f"https://www.target.com/s?searchTerm={query}"
    if "bhphotovideo.com" in hostname:
        return f"https://www.bhphotovideo.com/c/search?q={query}&sts=ma"
    if "walmart.com" in hostname:
        return f"https://www.walmart.com/search?q={query}"
    if "amazon." in hostname:
        return f"https://www.amazon.com/s?k={query}"
    if "newegg.com" in hostname:
        return f"https://www.newegg.com/p/pl?d={query}"

    return vendor_url


def build_goal_prompt(product_query: str, site_url: str, extra_notes: str = "") -> str:
    notes_line = ""
    if extra_notes.strip():
        notes_line = f"\nAdditional buyer constraints: {extra_notes.strip()}"

    schema = json.dumps(DEFAULT_RESULT_SCHEMA, indent=2)

    return (
        f"You are gathering a live buying signal from {site_url}.\n"
        f"Goal: find the best current listing for '{product_query}' directly on that website.\n\n"
        "Workflow:\n"
        "1. Stay on the target site itself. Do not use external search engines.\n"
        "2. If the starting page is already a search results page, use it immediately.\n"
        "3. Handle cookie banners, modals, and region selectors only if they block progress.\n"
        "4. Review up to the top 3 relevant matches and choose the strongest match.\n"
        "5. Extract the live listing URL, price, currency, stock or availability, and any useful shipping or return notes.\n"
        "6. If no reliable match exists, return the same JSON shape with null values and explain why in notes.\n"
        f"{notes_line}\n\n"
        "Return JSON only. No markdown fences. Use this exact schema:\n"
        f"{schema}\n\n"
        f"Set 'vendor' to '{vendor_name_from_url(site_url)}' and 'searched_product' to '{product_query}'. "
        "Use confidence = high, medium, or low."
    )


def normalize_result_payload(result: object) -> dict[str, object]:
    if isinstance(result, dict):
        data = dict(DEFAULT_RESULT_SCHEMA)
        data.update(result)
        return data

    if isinstance(result, str):
        try:
            parsed = json.loads(result)
        except json.JSONDecodeError:
            data = dict(DEFAULT_RESULT_SCHEMA)
            data["notes"] = result
            return data
        return normalize_result_payload(parsed)

    data = dict(DEFAULT_RESULT_SCHEMA)
    data["notes"] = repr(result)
    return data
