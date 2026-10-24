"""Read local sitemap pages for release checks and IndexNow; CLI prints page paths."""
import json
import xml.etree.ElementTree as ET
from pathlib import Path

NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"


def sitemap_urls(root, origin):
    tree = ET.parse(root / "sitemap.xml").getroot()
    maps = [tree]
    if tree.tag == NS + "sitemapindex":
        maps = []
        for child in tree.findall(NS + "sitemap"):
            loc = child.findtext(NS + "loc") or ""
            name = loc.removeprefix(origin + "/")
            if not loc.startswith(origin + "/") or "/" in name or not name.endswith(".xml"):
                raise ValueError(f"Invalid local sitemap reference: {loc}")
            maps.append(ET.parse(root / name).getroot())
    urls = []
    for tree in maps:
        if tree.tag != NS + "urlset":
            raise ValueError("Expected a sitemap urlset")
        for page in tree.findall(NS + "url"):
            loc = page.findtext(NS + "loc") or ""
            if not loc.startswith(origin + "/"):
                raise ValueError(f"Invalid sitemap page URL: {loc}")
            urls.append(loc)
    if not urls or len(urls) != len(set(urls)):
        raise ValueError("Sitemap page URLs are empty or duplicated")
    return urls


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    origin = json.loads((root / "tools/site.json").read_text())["site"]["origin"]
    print("\n".join(url[len(origin):] for url in sitemap_urls(root, origin)))
