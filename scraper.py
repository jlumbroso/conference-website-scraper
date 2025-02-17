#!/usr/bin/env python3

import sys
import time
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from collections import deque
from loguru import logger
import click
from click_help_colors import HelpColorsCommand


def is_same_domain(url, domain):
    """
    Checks whether `url` is in the same domain as `domain`.
    """
    parsed = urlparse(url)
    return parsed.netloc == domain


def clean_url(url):
    """
    Strips trailing slashes, query parameters, fragments, etc. if needed.
    You can customize based on how strictly you want to treat duplicates.
    """
    parsed = urlparse(url)
    # Rebuild without fragment (#...) and query (?...)
    return parsed.scheme + "://" + parsed.netloc + parsed.path


@click.command(
    cls=HelpColorsCommand,
    help_headers_color="cyan",
    help_options_color="magenta",
    context_settings=dict(help_option_names=["-h", "--help"]),
)
@click.option(
    "--start-url",
    default="https://sigcse2025.sigcse.org",
    show_default=True,
    help="Starting URL for the scraper.",
)
@click.option(
    "--output-json",
    default="sigcse2025_all_pages.json",
    show_default=True,
    help="Path to output JSON file.",
)
@click.option(
    "--restrict-navbar/--no-restrict-navbar",
    default=True,
    show_default=True,
    help="If True, only follow links within the div#navigationbar.",
)
def scrape_website_cli(start_url, output_json, restrict_navbar):
    """
    A conference website scraper that:
      - Crawls from START_URL
      - Restricts to the same domain
      - By default, only follows links within div#navigationbar
      - Stores pages in OUTPUT_JSON
    """
    # Configure loguru to log at DEBUG level to stderr
    logger.remove()  # Remove any default handlers
    logger.add(sys.stderr, level="DEBUG")

    domain = urlparse(start_url).netloc
    queue = deque([start_url])
    visited = set()
    scraped_pages = []

    logger.debug("Starting crawl from: {}", start_url)
    logger.debug("Output JSON: {}", output_json)
    logger.debug("Restrict to #navigationbar links: {}", restrict_navbar)

    while queue:
        current_url = queue.popleft()
        current_url = clean_url(current_url)

        if current_url in visited:
            continue
        visited.add(current_url)

        logger.debug("Scraping: {}", current_url)
        try:
            response = requests.get(current_url, timeout=10)
            if response.status_code != 200:
                logger.debug(
                    "Skipping {} (status code {})", current_url, response.status_code
                )
                continue
        except requests.RequestException as e:
            logger.debug("Request failed for {}: {}", current_url, e)
            continue

        page_html = response.text
        scraped_pages.append({"url": current_url, "html": page_html})

        # Parse the HTML
        soup = BeautifulSoup(page_html, "html.parser")

        if restrict_navbar:
            # Only parse links within the nav div with id="navigationbar"
            nav_div = soup.find("div", id="navigationbar")
            if nav_div:
                link_tags = nav_div.find_all("a", href=True)
            else:
                # If no #navigationbar found, no new links
                link_tags = []
        else:
            # Parse *all* links from the page
            link_tags = soup.find_all("a", href=True)

        for link in link_tags:
            href = link.get("href")
            abs_url = urljoin(current_url, href)
            abs_url = clean_url(abs_url)

            # Enqueue only if same domain and not visited
            if is_same_domain(abs_url, domain) and abs_url not in visited:
                queue.append(abs_url)

        # Optional: be polite to the server
        # time.sleep(1)

    # Write the scraped data to JSON
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(scraped_pages, f, indent=2, ensure_ascii=False)

    logger.debug(
        "Done! Scraped {} pages. Results saved to {}", len(scraped_pages), output_json
    )


if __name__ == "__main__":
    scrape_website_cli()
