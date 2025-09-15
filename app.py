def clean_html(soup):
    # წაშლის <style>, <script>, <svg>
    for tag in soup(["style", "script", "svg", "noscript"]):
        tag.decompose()

    # base64 img → noscript fallback
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if src.startswith("data:image"):
            img.decompose()

    # ატრიბუტების გაწმენდა
    for tag in soup.find_all(True):
        if tag.name == "a":
            if "href" in tag.attrs:
                del tag.attrs["href"]

        elif tag.name == "img":
            src = tag.get("src")
            alt = tag.get("alt", "").strip() or "Image"
            tag.attrs = {"src": src, "alt": alt}

        else:
            for attr in list(tag.attrs.keys()):
                if attr not in ["src", "alt"]:
                    del tag.attrs[attr]

    # ზედმეტი div-ების გაწმენდა
    for div in soup.find_all("div"):
        # თუ div-ს არ აქვს class/id და შიგნით მხოლოდ ერთი შვილობაა → unwrap
        if not div.attrs and len(div.contents) == 1:
            div.unwrap()
        # თუ div ცარიელია → წაშლა
        elif not div.attrs and not div.get_text(strip=True) and not div.find("img"):
            div.decompose()

    return soup
