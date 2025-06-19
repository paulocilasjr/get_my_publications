import argparse
import json
from datetime import datetime
from serpapi import GoogleSearch
from dotenv import load_dotenv
import os
import time

# Load environment variables from .env file
load_dotenv()
API_KEY = os.getenv("API_KEY")

def parse_date(date_str):
    try:
        return datetime.strptime(date_str.strip(), "%Y/%m/%d")
    except ValueError:
        try:
            return datetime.strptime(date_str.strip(), "%Y/%m")
        except ValueError:
            try:
                return datetime.strptime(date_str.strip(), "%Y")
            except ValueError:
                return datetime.max  # Place undated entries at the end

def get_publications_from_serpapi(user_id):
    all_publications = []
    next_token = None

    while True:
        time.sleep(1)
    all_publications = []
    next_token = None

    while True:
        params = {
            "engine": "google_scholar_author",
            "author_id": user_id,
            "api_key": API_KEY,
            "hl": "en"
        }

        if next_token:
            params["after_author"] = next_token

        search = GoogleSearch(params)
        results = search.get_dict()

        articles = results.get("articles", [])
        if not articles:
            break

        all_publications.extend(articles)
        print(f"Fetched {len(all_publications)} total articles so far...")

        # Check for next page token
        next_token = results.get("cited_by", {}).get("next", {}).get("token")
        if not next_token:
            break

    return all_publications

def build_metadata_from_article(article):
    result = {
        "Title": article.get("title"),
        "Link": article.get("link"),
        "Authors": article.get("authors"),
        "Journal": article.get("publication"),
        "Publication date": article.get("year")
    }
    return {k: v for k, v in result.items() if v is not None}

def main(user_id):
    if not API_KEY:
        print("❌ Error: API_KEY not found in environment. Please create a .env file with API_KEY=your_key.")
        return

    print(f"Fetching citations for user: {user_id} using SerpAPI")
    articles = get_publications_from_serpapi(user_id)
    print(f"Found {len(articles)} articles.")

    all_data = []
    for i, article in enumerate(articles, 1):
        print(f"[{i}/{len(articles)}] Processing: {article.get('title', 'No Title')}")
        citation_data = build_metadata_from_article(article)
        if citation_data:
            citation_data["__parsed_date__"] = parse_date(citation_data.get("Publication date", ""))
            all_data.append(citation_data)

    journal_entries = []
    other_entries = []

    for entry in all_data:
        if "Journal" in entry:
            journal_entries.append(entry)
        else:
            other_entries.append(entry)

    journal_entries.sort(key=lambda x: x["__parsed_date__"])
    other_entries.sort(key=lambda x: x["__parsed_date__"])

    for e in journal_entries + other_entries:
        e.pop("__parsed_date__", None)

    final_json = {
        "Journal": journal_entries,
        "others": other_entries
    }

    output_filename = f"scholar_data_{user_id}.json"
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(final_json, f, indent=2, ensure_ascii=False)

    print(f"✅ Saved sorted data to {output_filename}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape Google Scholar publications using SerpAPI.")
    parser.add_argument("user_id", help="Google Scholar user ID (e.g. hWjExXQAAAAJ)")
    args = parser.parse_args()
    main(args.user_id)

