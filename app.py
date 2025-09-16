import os
import re
import logging
import requests
from flask import Flask, request, jsonify
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response

def extract_images(soup, image_urls):
    # --- img tag variations ---
    for img in soup.find_all("img"):
        src = (
            img.get("src")
            or img.get("data-src")
            or img.get("data-lazy")
            or img.get("data-original")
            or img.get("data-background")
        )
        # srcset-ის დამუშავება
        if not src and img.get("srcset"):
            src = img["srcset"].split(",")[0].split()[0]

        if not src:
            continue

        if src.startswith("//"):
            src = "https:" + src
        if src.startswith("http"):
            image_urls.add(src)

        alt = img.get("alt", "").strip() or "Image"
        img.attrs = {"src": src, "alt": alt}

    # --- background-image inline style ---
    for div in soup.find_all(style=True):
        style = div["style"]
        m = re.search(r"url\((.*?)\)", style)
        if m:
            url = m.group(1).strip("\"' ")
            if url.startswith("//"):
                url = "https:" + url
            if url.startswith("http"):
                image_urls.add(url)

    return image_urls

def clean_html(soup, image_urls):
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()

    extract_images(soup, image_urls)

    # <a> → href წაშლა
    for a in soup.find_all("a"):
        if "href" in a.attrs:
            del a.attrs["href"]

    # სხვა ტეგების ატრიბუტების გაწმენდა
    for tag in soup.find_all(True):
        if tag.name != "img":
            for attr in list(tag.attrs.keys()):
                if attr not in ["src", "alt"]:
                    del tag.attrs[attr]

    return soup

def extract_blog_content(html: str):
    soup = BeautifulSoup(html, "html.parser")
    image_urls = set()

    # სათაური
    title = None
    for t in ["h1", "h2", "title"]:
        el = soup.find(t)
        if el and el.get_text(strip=True):
            title = el.get_text(strip=True)
            break

    # მთავარი article/content
    article = None
    candidates = [
        "article",
        "div[class*='content']",
        "div[class*='entry']",
        "div[class*='post']",
        "div[class*='blog']",
        "main"
    ]
    for sel in candidates:
        el = soup.select_one(sel)
        if el and len(el.get_text(strip=True)) > 200:
            article = el
            break

    if not article:
        article = soup.body or soup

    # ზედმეტის წაშლა
    remove_selectors = [
        "aside", "nav", "footer", "header",
        "form", "button", ".share", ".tags",
        ".author", ".related"
    ]
    for sel in remove_selectors:
        for tag in article.select(sel):
            tag.decompose()

    article = clean_html(article, image_urls)

    return {
        "title": title or "Untitled",
        "content_html": str(article).strip(),
        "images": list(image_urls)
    }

@app.route("/scrape-blog", methods=["POST"])
def scrape_blog():
    try:
        data = request.get_json(force=True)
        url = data.get("url")
        if not url:
            return jsonify({"error": "Missing 'url' field"}), 400

        resp = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()

        result = extract_blog_content(resp.text)
        return jsonify(result)

    except Exception as e:
        logging.exception("Error scraping blog")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
