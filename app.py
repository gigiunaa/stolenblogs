import os
import logging
import requests
from flask import Flask, request, jsonify
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

def extract_blog_content(html: str):
    soup = BeautifulSoup(html, "html.parser")

    # მთავარი article მოძებნე
    article = soup.find("article")
    if not article:
        for cls in ["blog-content", "post-content", "entry-content", "content", "article-body"]:
            article = soup.find("div", class_=cls)
            if article:
                break

    if not article:
        article = soup.body

    # ❌ წაშლის selectors – აქ შეგიძლია დაამატო რაც არ გინდა
    remove_selectors = [
        "ul.entry-meta",           # ავტორი + თარიღი
        "div.entry-tags",          # tags
        "div.ct-share-box",        # share
        "div.author-box",          # author bio
        "nav.post-navigation",     # next/prev
        "div.wp-block-buttons",    # CTA
        "aside",                   # side widgets
        "header .entry-meta",      # header meta
        "footer"                   # footer
    ]
    for sel in remove_selectors:
        for tag in article.select(sel):
            tag.decompose()

    # ❌ წავშალოთ ყველა inline style
    for tag in article.find_all(style=True):
        del tag["style"]

    return article

@app.route("/scrape-blog", methods=["POST"])
def scrape_blog():
    try:
        data = request.get_json(force=True)
        url = data.get("url")
        if not url:
            return jsonify({"error": "Missing 'url' field"}), 400

        resp = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()

        article = extract_blog_content(resp.text)
        if not article:
            return jsonify({"error": "Could not extract blog content"}), 422

        # სუფთა HTML
        clean_html = str(article).strip()

        # სურათების ამოღება
        images = [img.get("src") for img in article.find_all("img") if img.get("src")]

        return jsonify({
            "html": clean_html,
            "images": images
        })

    except Exception as e:
        logging.exception("Error scraping blog")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
