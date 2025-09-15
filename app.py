import os
import logging
import requests
from flask import Flask, request, jsonify
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

def extract_blog_content(html: str):
    soup = BeautifulSoup(html, "html.parser")
    article = soup.find("article")
    if not article:
        for cls in ["blog-content", "post-content", "entry-content", "content", "article-body"]:
            article = soup.find("div", class_=cls)
            if article:
                break
    content = article if article else soup.body
    return content

@app.route("/scrape-blog", methods=["POST"])
def scrape_blog():
    try:
        data = request.get_json(force=True)
        url = data.get("url")
        if not url:
            return jsonify({"error": "Missing 'url' field"}), 400

        resp = requests.get(url, timeout=20)
        resp.raise_for_status()

        soup = extract_blog_content(resp.text)
        if not soup:
            return jsonify({"error": "Could not extract blog content"}), 422

        clean_html = str(soup)
        images = [img.get("src") for img in soup.find_all("img") if img.get("src")]

        return jsonify({"html": clean_html.strip(), "images": images})
    except Exception as e:
        logging.exception("Error scraping blog")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
