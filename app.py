import os
import logging
import requests
from flask import Flask, request, Response
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

    return article

def clean_html(soup):
    # წაშლის <style> და <script>
    for tag in soup(["style", "script"]):
        tag.decompose()

    for tag in soup.find_all(True):
        if tag.name == "a":
            # მოვაშოროთ href, მაგრამ ტექსტი/შიდა ელემენტები დარჩეს
            if "href" in tag.attrs:
                del tag.attrs["href"]

        elif tag.name == "img":
            # დავტოვოთ მხოლოდ src და alt
            src = tag.get("src")
            alt = tag.get("alt", "").strip() or "Image"
            tag.attrs = {"src": src, "alt": alt}

        else:
            # class, id, style და სხვა ზედმეტი ატრიბუტების წაშლა
            for attr in list(tag.attrs.keys()):
                if attr not in ["src", "alt"]:  # სურათის შემთხვევაში დავტოვებთ
                    del tag.attrs[attr]

    return soup

@app.route("/scrape-blog", methods=["POST"])
def scrape_blog():
    try:
        data = request.get_json(force=True)
        url = data.get("url")
        if not url:
            return Response("Missing 'url' field", status=400)

        resp = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()

        article = extract_blog_content(resp.text)
        if not article:
            return Response("Could not extract blog content", status=422)

        # გაწმენდა
        clean_article = clean_html(article)

        clean_html_str = str(clean_article).strip()
        return Response(clean_html_str, mimetype="text/html")

    except Exception as e:
        logging.exception("Error scraping blog")
        return Response(f"Error: {str(e)}", status=500)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
