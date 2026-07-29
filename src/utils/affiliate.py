from urllib.parse import urlencode, urlparse, urlunparse


def make_affiliate_url(clean_url: str, platform: str, affiliate_config: dict) -> str:
    if not affiliate_config:
        return clean_url
    tag = affiliate_config.get(platform)
    if not tag:
        return clean_url

    parsed = urlparse(clean_url)
    params = {}

    if platform == "ML" and tag.startswith("matt:"):
        parts = tag.split(":")
        if len(parts) >= 3:
            params["matt_word"] = parts[1]
            params["matt_tool"] = parts[2]
    elif platform == "AZ":
        params["tag"] = tag
    else:
        params["tag"] = tag

    existing = parsed.query
    new_query = urlencode(params)
    query = f"{existing}&{new_query}" if existing else new_query
    return urlunparse(parsed._replace(query=query))
