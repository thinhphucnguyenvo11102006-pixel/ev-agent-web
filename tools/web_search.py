"""
E.V. Web Search — Multi-engine web search (DuckDuckGo + Fallback).
"""

import urllib.request
import urllib.parse
import json
import logging
import re
from typing import List, Dict

logger = logging.getLogger("ev.tools.web_search")


def web_search(query: str, num_results: int = 5) -> str:
    """
    Search the web using DuckDuckGo with automatic fallback.
    """
    num_results = min(max(num_results, 1), 10)

    # Method 1: DuckDuckGo DDGS library
    try:
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS

        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=num_results))

        if results:
            output_lines = [f"🔍 Search results for: {query}\n"]
            for i, r in enumerate(results, 1):
                title = r.get("title", "No title")
                body = r.get("body", "No description")
                href = r.get("href", "")
                output_lines.append(f"{i}. **{title}**")
                output_lines.append(f"   {body}")
                if href:
                    output_lines.append(f"   URL: {href}")
                output_lines.append("")
            return "\n".join(output_lines)

    except Exception as e:
        logger.warning(f"DuckDuckGo DDGS search failed ({e}), trying fallback API...")

    # Method 2: DuckDuckGo Instant Answer API Fallback
    try:
        encoded = urllib.parse.quote(query)
        url = f"https://api.duckduckgo.com/?q={encoded}&format=json&no_html=1&skip_disambig=1"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        abstract = data.get("AbstractText", "")
        heading = data.get("Heading", query)
        source_url = data.get("AbstractURL", "")

        if abstract:
            return f"🔍 Search result for: {heading}\n\n**{heading}**\n{abstract}\nURL: {source_url}"

        related = data.get("RelatedTopics", [])
        if related:
            lines = [f"🔍 Search results for: {query}\n"]
            count = 0
            for item in related:
                if "Text" in item and "FirstURL" in item:
                    count += 1
                    lines.append(f"{count}. {item['Text']}\n   URL: {item['FirstURL']}\n")
                    if count >= num_results:
                        break
            if count > 0:
                return "\n".join(lines)

    except Exception as ex:
        logger.warning(f"DuckDuckGo API fallback failed: {ex}")

    return f"No search results found for: {query}"
