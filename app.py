# blog_scraper.py
# -*- coding: utf-8 -*-

import os
import re
import json
import logging
import requests
from flask import Flask, request, Response
from flask_cors import CORS
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)
CORS(app)

# ------------------------------
# Helper: გაწმენდა
# ------------------------------
def clean_html(soup):
    # წაშლის <style>, <script>
    for tag in soup(["style", "script", "svg", "noscript"]):
        tag.decompose()

    return soup

# ------------------------------
# Helper: ამოიღოს სურათები
# ------------------------------
def extract_images(soup):
    image_urls = set()

    # 1. <img> + lazy attributes + srcset
    for img in soup.find_all("img"):
        src = (
            img.get("src")
            or img.get("data-src")
            or img.get("data-lazy-src")
            or img.get("data-original")
            or img.get("data-background")
        )
        if not src and img.get("srcset"):
            src = img["srcset"].split(",")[0].split()[0]

        if src:
            if src.startswith("//"):
                src = "https:" + src
            if src.startswith(("http://", "https://")):
                image_urls.add(src)

    # 2. <source srcset="..."> (მაგ. <picture>)
    for source in soup.find_all("source"):
        srcset = source.get("srcset")
        if srcset:
            first = srcset.split(",")[0].split()[0]
            if first.startswith("//"):
                first = "https:" + first
            if first.startswith(("http://", "https://")):
                image_urls.add(first)

    # 3. style="background-image:url(...)"
    for tag in soup.find_all(style=True):
        style = tag["style"]
        for match in re.findall(r"url\((.*?)\)", style):
            url = match.strip("\"' ")
            if url.startswith("//"):
                url = "https:" + url
            if url.startswith(("http://", "https://")):
                image_urls.add(url)

    return list(image_urls)

# ------------------------------
# Helper: ამოიღოს article
# ------------------------------
def extract_blog_content(html: str):
    soup = BeautifulSoup(html, "html.parser")

    # მთავარი article მოძებნე
    article = soup.find("article")
    if not article:
        for cls in [
            "blog-content",
            "post-content",
            "entry-content",
            "content",
            "article-body",
        ]:
            article = soup.find("div", class_=cls)
            if article:
                break

    if not article:
        article = soup.body

    # წასაშლელი selectors
    remove_selectors = [
        "ul.entry-meta",
        "div.entry-tags",
        "div.ct-share-box",
        "div.author-box",
        "nav.post-navigation",
        "div.wp-block-buttons",
        "aside",
        "header .entry-meta",
        "footer",
    ]
    for sel in remove_selectors:
        for tag in article.select(sel):
            tag.decompose()

    # გაწმენდა
    article = clean_html(article)

    return article

# ------------------------------
# API route
# ------------------------------
@app.route("/scrape-blog", methods=["POST"])
def scrape_blog():
    try:
        data = request.get_json(force=True)
        url = data.get("url")
        if not url:
            return Response("Missing 'url' field", status=400)

        resp = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        # სათაური
        title = None
        if soup.title:
            title = soup.title.string.strip()
        h1 = soup.find("h1")
        if h1 and not title:
            title = h1.get_text(strip=True)

        # ბლოგის კონტენტი
        article = extract_blog_content(resp.text)
        if not article:
            return Response("Could not extract blog content", status=422)

        # სურათები
        images = extract_images(soup)

        result = {
            "title": title or "",
            "content_html": str(article).strip(),
            "images": images,
        }

        return Response(json.dumps(result, ensure_ascii=False), mimetype="application/json")

    except Exception as e:
        logging.exception("Error scraping blog")
        return Response(f"Error: {str(e)}", status=500)

# ------------------------------
# Run
# ------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
