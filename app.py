import os
import logging
import requests
from flask import Flask, request, Response
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

def extract_blog_content(html: str):
    soup = BeautifulSoup(html, "html.parser")

    # მოძებნე მთავარი article
    article = soup.find("article")
    if not article:
        for cls in ["blog-content", "post-content", "entry-content", "content", "article-body"]:
            article = soup.find("div", class_=cls)
            if article:
                break

    if not article:
        return None

    # ❌ წაშალე არასასურველი ბლოკები
    remove_selectors = [
        "div.wp-block-buttons",    # CTA buttons
        "div.entry-tags",          # Tags
        "div.ct-share-box",        # Share box
        "div.author-box",          # Author box
        "nav.post-navigation"      # Next/Prev navigation
    ]
    for sel in remove_selectors:
        for tag in article.select(sel):
            tag.decompose()

    return article

@app.route("/scrape-blog", methods=["POST"])
def scrape_blog():
    try:
        data = request.get_json(force=True)
        url = data.get("url")
        if not url:
            return Response("Missing 'url' field", status=400)

        resp = requests.get(url, timeout=20)
        resp.raise_for_status()

        soup = extract_blog_content(resp.text)
        if not soup:
            return Response("Could not extract blog content", status=422)

        clean_html = str(soup).strip()
        return Response(clean_html, mimetype="text/html")

    except Exception as e:
        logging.exception("Error scraping blog")
        return Response(f"Error: {str(e)}", status=500)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
