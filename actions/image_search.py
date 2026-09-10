"""
image_search.py — Web Diagram & Schematic Image Searcher for AURA 3D Learning Lab

Searches the web for high-resolution schematics, technical diagrams, and educational illustrations
and downloads them for interactive viewing in the 3D Lab.
"""

from __future__ import annotations

import hashlib
import logging
import os
import tempfile
from pathlib import Path
from typing import List, Dict, Optional

import requests

logger = logging.getLogger("image_search")

CACHE_DIR = Path(tempfile.gettempdir()) / "aura_3d_images"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _get_cache_path(url: str) -> Path:
    url_hash = hashlib.md5(url.encode("utf-8")).hexdigest()
    ext = os.path.splitext(url.split("?")[0])[-1].lower()
    if ext not in (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"):
        ext = ".jpg"
    return CACHE_DIR / f"{url_hash}{ext}"


def search_diagram_images(query: str, max_results: int = 6) -> List[Dict[str, str]]:
    """
    Search the web for technical diagrams and schematics for a concept or device.
    Uses DuckDuckGo images and Wikimedia Commons schematics.
    """
    clean_query = query.strip()
    if not clean_query:
        return []

    results: List[Dict[str, str]] = []
    seen_urls = set()

    # 1. Try DuckDuckGo Image Search
    search_terms = [
        f"{clean_query} diagram schematic labeled",
        f"{clean_query} technical diagram",
    ]

    for term in search_terms:
        if len(results) >= max_results:
            break
        try:
            try:
                from ddgs import DDGS
            except ImportError:
                from duckduckgo_search import DDGS

            with DDGS() as ddgs:
                try:
                    ddg_results = ddgs.images(term, max_results=max_results)
                except TypeError:
                    ddg_results = ddgs.images(keywords=term, max_results=max_results)
                for item in ddg_results:
                    img_url = item.get("image") or item.get("thumbnail")
                    if img_url and img_url not in seen_urls:
                        seen_urls.add(img_url)
                        results.append({
                            "title": item.get("title") or f"{clean_query} Diagram",
                            "image": img_url,
                            "thumbnail": item.get("thumbnail") or img_url,
                            "source": item.get("url") or "",
                        })
                    if len(results) >= max_results:
                        break
        except Exception as e:
            logger.debug(f"DDG search unavailable for '{term}': {e}")

    # 2. Fallback to Wikimedia Commons API if needed
    if len(results) < max_results:
        try:
            wiki_url = "https://commons.wikimedia.org/w/api.php"
            params = {
                "action": "query",
                "generator": "search",
                "gsrsearch": f"{clean_query} diagram schematic",
                "gsrnamespace": "6",
                "gsrlimit": str(max_results * 2),
                "prop": "imageinfo",
                "iiprop": "url|size|mime",
                "format": "json"
            }
            headers = {"User-Agent": "Aura3DLab/1.0 (educational research)"}
            resp = requests.get(wiki_url, params=params, headers=headers, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                pages = data.get("query", {}).get("pages", {})
                for pid, page in pages.items():
                    title = page.get("title", "").replace("File:", "")
                    img_infos = page.get("imageinfo", [])
                    if img_infos:
                        img_url = img_infos[0].get("url", "")
                        mime = img_infos[0].get("mime", "")
                        if img_url and img_url not in seen_urls and not mime.endswith("pdf"):
                            seen_urls.add(img_url)
                            results.append({
                                "title": title,
                                "image": img_url,
                                "thumbnail": img_url,
                                "source": f"https://commons.wikimedia.org/wiki/{page.get('title', '')}"
                            })
                    if len(results) >= max_results:
                        break
        except Exception as e:
            logger.warning(f"Wikimedia search fallback failed: {e}")

    return results


def download_image_bytes(url: str, timeout: int = 8) -> Optional[bytes]:
    """Download image bytes with local disk caching."""
    if not url:
        return None

    cache_file = _get_cache_path(url)
    if cache_file.exists() and cache_file.stat().st_size > 500:
        try:
            return cache_file.read_bytes()
        except Exception:
            pass

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        )
    }

    try:
        resp = requests.get(url, headers=headers, timeout=timeout)
        if resp.status_code == 200 and len(resp.content) > 500:
            try:
                cache_file.write_bytes(resp.content)
            except Exception:
                pass
            return resp.content
    except Exception as e:
        logger.warning(f"Failed to download image from {url}: {e}")

    return None
