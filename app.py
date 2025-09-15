import os
import logging
import requests
from flask import Flask, request, Response
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
            return Response("Missing 'url' field", status=400)

        resp = requests.get(url, timeout=20)
        resp.raise_for_status()

        soup = extract_blog_content(resp.text)
        if not soup:
            return Response("Could not extract blog content", status=422)

        clean_html = str(soup).strip()

        # ❗ დააბრუნე პირდაპირ HTML
        return Response(clean_html, mimetype="text/html")

    except Exception as e:
        logging.exception("Error scraping blog")
        return Response(f"Error: {str(e)}", status=500)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
