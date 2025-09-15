import os
import logging
import requests
from flask import Flask, request, jsonify
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

def clean_html(soup):
    # წაშლის <style>, <script>, <svg>
    for tag in soup(["style", "script", "svg"]):
        tag.decompose()

    for tag in soup.find_all(True):
        if tag.name == "a":
            # მოვაშოროთ href, მაგრამ ტექსტი დარჩეს
            if "href" in tag.attrs:
                del tag.attrs["href"]

        elif tag.name == "img":
            # დავტოვოთ მხოლოდ src და alt
            src = tag.get("src")
            alt = tag.get("alt", "").strip() or "Image"
            tag.attrs = {"src": src, "alt": alt}

        else:
            # class, id, style და სხვა ატრიბუტების წაშლა
            for attr in list(tag.attrs.keys()):
                if attr not in ["src", "alt"]:
                    del tag.attrs[attr]

    return soup

def extract_blog_content(html: str):
    soup = BeautifulSoup(html, "html.parser")

    article = soup.find("article")
    if not article:
        for cls in ["blog-content", "post-content", "entry-content", "content", "article-body"]:
            article = soup.find("div", class_=cls)
            if article:
                break

    if not article:
        article = soup.body

    # unwanted selectors
    remove_selectors = [
        "ul.entry-meta",
        "div.entry-tags",
        "div.ct-share-box",
        "div.author-box",
        "nav.post-navigation",
        "div.wp-block-buttons",
        "aside",
        "header .entry-meta",
        "footer"
    ]
    for sel in remove_selectors:
        for tag in article.select(sel):
            tag.decompose()

    # გავასუფთავოთ
    clean_article = clean_html(article)

    # სურათების ამოღება
    images = [img["src"] for img in clean_article.find_all("img") if img.get("src")]

    return str(clean_article), images

@app.route("/scrape-blog", methods=["POST"])
def scrape_blog():
    try:
        data = request.get_json(force=True)
        url = data.get("url")
        if not url:
            return jsonify({"error": "Missing 'url'"}), 400

        resp = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()

        html, images = extract_blog_content(resp.text)

        return jsonify({
            "html": html.strip(),
            "images": images
        })

    except Exception as e:
        logging.exception("Error scraping blog")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
