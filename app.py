import os
import re
import logging
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)
CORS(app)  # საშუალებას აძლევს ნებისმიერ Origin-ს

def extract_images(soup, image_urls):
    # <img> ტეგები
    for img in soup.find_all("img"):
        src = (
            img.get("src")
            or img.get("data-src")
            or img.get("data-lazy")
            or img.get("data-original")
        )
        if not src:
            continue
        alt = img.get("alt", "").strip() or "Image"
        img.attrs = {"src": src, "alt": alt}
        if src.startswith("http"):
            image_urls.add(src)

    # background-image style-დან
    for div in soup.find_all(style=True):
        style = div["style"]
        m = re.search(r"url\((.*?)\)", style)
        if m:
            url = m.group(1).strip("\"' ")
            if url.startswith("http"):
                image_urls.add(url)

    return image_urls

def clean_html(soup, image_urls):
    # წაშლის script, style, noscript
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()

    # სურათების დამუშავება
    extract_images(soup, image_urls)

    # <a> ბმულებიდან href წაიშლება
    for a in soup.find_all("a"):
        if "href" in a.attrs:
            del a.attrs["href"]

    # ყველა სხვა ტეგს ვუტოვებთ მხოლოდ src/alt თუ აქვს
    for tag in soup.find_all(True):
        if tag.name != "img":
            for attr in list(tag.attrs.keys()):
                if attr not in ["src", "alt"]:
                    del tag.attrs[attr]

    return soup

def extract_blog_content(html: str):
    soup = BeautifulSoup(html, "html.parser")
    image_urls = set()

    # სათაური მოძებნე
    title = None
    for t in ["h1", "h2", "title"]:
        el = soup.find(t)
        if el and el.get_text(strip=True):
            title = el.get_text(strip=True)
            break

    # მთავარი article
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

    # ზედმეტი ელემენტების წაშლა
    remove_selectors = [
        "aside", "nav", "footer", "header",
        "form", "button", ".share", ".tags",
        ".author", ".related"
    ]
    for sel in remove_selectors:
        for tag in article.select(sel):
            tag.decompose()

    # გაწმენდა
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
