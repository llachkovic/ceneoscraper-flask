from requests import get, codes
from bs4 import BeautifulSoup

# from translate import Translator
import re


def scrape_product_reviews(product_code):
    def get_element(ancestor, selector=None, attribute=None, return_list=False):
        try:
            if return_list:
                return ", ".join(
                    [tag.text.strip() for tag in ancestor.select(selector)]
                )
            if not selector and attribute:
                return ancestor[attribute]
            if attribute:
                return ancestor.select_one(selector)[attribute].strip()
            return ancestor.select_one(selector).text.strip()
        except (AttributeError, TypeError):
            return None

    selectors = {
        "id": [None, "data-entry-id"],
        "author": ["span.user-post__author-name"],
        "recommendation": ["span.user-post__author-recomendation > em"],
        "stars": ["span.user-post__score-count"],
        "content": ["div.user-post__text"],
        "pros": [
            "div.review-feature__title--positives ~ div.review-feature__item",
            None,
            True,
        ],
        "cons": [
            "div.review-feature__title--negatives ~ div.review-feature__item",
            None,
            True,
        ],
        "upvote": ["button.vote-yes", "data-total-vote"],
        "downvote": ["button.vote-no", "data-total-vote"],
        "posted": ["span.user-post__published > time:nth-child(1)", "datetime"],
        "purchased": ["span.user-post__published > time:nth-child(2)", "datetime"],
    }

    lang_from = "pl"
    lang_to = "en"
    # translator = Translator(lang_to, lang_from)

    def translate(text):
        # if text:
        # return translator.translate(text)
        return None

    url = f"https://www.ceneo.pl/{product_code}#tab=reviews"
    all_opinions = []

    while url:
        print(url)
        response = get(url)
        if response.status_code != codes["ok"]:
            raise Exception(
                f"Failed to retrieve data. Status code: {response.status_code}"
            )

        page_dom = BeautifulSoup(response.text, "html.parser")
        opinions = page_dom.select("div.js_product-review")

        for opinion in opinions:
            single_opinion = {}
            for key, value in selectors.items():
                single_opinion[key] = get_element(opinion, *value)

            single_opinion["recommendation"] = (
                True
                if single_opinion["recommendation"] == "Polecam"
                else False
                if single_opinion["recommendation"] == "Nie polecam"
                else None
            )
            single_opinion["stars"] = float(
                single_opinion["stars"].split("/")[0].replace(",", ".")
            )
            single_opinion["upvote"] = int(single_opinion["upvote"])
            single_opinion["downvote"] = int(single_opinion["downvote"])
            single_opinion["content"] = " ".join(
                re.sub(r"\s+", " ", single_opinion["content"], flags=re.UNICODE).split(
                    " "
                )
            )
            # single_opinion["content_en"] = translate(single_opinion["content"])
            # single_opinion["pros_en"] = translate(single_opinion["pros"])
            # single_opinion["cons_en"] = translate(single_opinion["cons"])
            all_opinions.append(single_opinion)

        try:
            url = "https://www.ceneo.pl" + get_element(
                page_dom, "a.pagination__next", "href"
            )
        except TypeError:
            url = None

    return all_opinions
