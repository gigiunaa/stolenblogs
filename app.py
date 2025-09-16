import os
import logging
import requests
from flask import Flask, request, jsonify
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

def clean_html(soup, image_urls):
    # წაშლის <style>, <script>, <svg>, <noscript>
    for tag in soup(["style", "script", "svg", "noscript"]):
        tag.decompose()

    # base64 img → ამოშლა
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if not src:
            img.decompose()
            continue

        if src.startswith("data:image"):
            img.decompose()
        else:
            alt = img.get("alt", "").strip() or "Image"
            img.attrs = {"src": src, "alt": alt}
            if src.startswith("http"):
                image_urls.add(src)

    # ლინკების გაწმენდა
    for tag in soup.find_all("a"):
        if "href" in tag.attrs:
            del tag.attrs["href"]

    # სხვა ტეგების გაწმენდა
    for tag in soup.find_all(True):
        if tag.name not in ["img"]:
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

    # მთავარი კონტენტი
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
        "aside",
        "nav",
        "footer",
        "header",
        "form",
        "button",
        ".share",
        ".tags",
        ".author",
        ".related",
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
