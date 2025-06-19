import argparse
import json
from datetime import datetime
from serpapi import GoogleSearch
from dotenv import load_dotenv
import os
from time import sleep

# Load .env file for API key
load_dotenv()
API_KEY = os.getenv("API_KEY")

def parse_date(date_str):
    """Convert a date string to a datetime object for sorting. Use datetime.min for missing/unparsable dates."""
    if not date_str:
        return datetime.min  # Treat missing dates as the earliest possible
    try:
        return datetime.strptime(date_str.strip(), "%Y/%m/%d")
    except ValueError:
        try:
            return datetime.strptime(date_str.strip(), "%Y/%m")
        except ValueError:
            try:
                return datetime.strptime(date_str.strip(), "%Y")
            except ValueError:
                return datetime.min  # Default for unparsable dates

def get_all_citation_ids_and_metadata(user_id):
    """Fetch all citations for a user from Google Scholar via SerpAPI."""
    if not API_KEY:
        raise RuntimeError("Missing API_KEY in .env file")

    print("Querying SerpAPI for all citations...")
    all_articles = []
    next_token = None
    page = 1

    while True:
        sleep(5)  # Avoid hitting API rate limits
        params = {
            "engine": "google_scholar_author",
            "author_id": user_id,
            "api_key": API_KEY,
            "hl": "en",
            "num": "100"  # Maximum results per request
        }
        if next_token:
            params["after_author"] = next_token

        search = GoogleSearch(params)
        results = search.get_dict()

        if "error" in results:
            raise RuntimeError(f"SerpAPI error: {results['error']}")

        articles = results.get("articles", [])
        if not articles:
            break

        all_articles.extend(articles)
        print(f"[Page {page}] Fetched {len(articles)} articles, total so far: {len(all_articles)}")

        next_url = results.get("next")
        if next_url and "after_author=" in next_url:
            from urllib.parse import parse_qs, urlparse
            query = urlparse(next_url).query
            next_token_list = parse_qs(query).get("after_author")
            next_token = next_token_list[0] if next_token_list else None
        else:
            break

        page += 1

    citations = []
    for article in all_articles:
        citation_id = article.get("citation_id")
        metadata = {
            "Title": article.get("title"),
            "Authors": article.get("authors"),
            "Journal": article.get("publication"),
            "Publication date": article.get("year"),
            "Link": article.get("link"),
            "Citation ID": citation_id
        }
        citations.append({k: v for k, v in metadata.items() if v})

    return citations

def main(user_id):
    """Fetch and sort citations by date (newest first), with missing dates at the bottom."""
    print(f"Fetching citations for user: {user_id}")
    try:
        all_data = get_all_citation_ids_and_metadata(user_id)
    except RuntimeError as e:
        print(f"❌ {e}")
        return

    journal_entries = []
    other_entries = []

    # Parse dates and categorize entries
    for entry in all_data:
        date_str = entry.get("Publication date", "")
        entry["__parsed_date__"] = parse_date(date_str)
        if "Journal" in entry:
            journal_entries.append(entry)
        else:
            other_entries.append(entry)

    # Sort in descending order (newest first), missing dates go to the bottom
    journal_entries.sort(key=lambda x: x["__parsed_date__"], reverse=True)
    other_entries.sort(key=lambda x: x["__parsed_date__"], reverse=True)

    # Remove temporary parsed date field
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
    parser = argparse.ArgumentParser(description="Scrape Google Scholar user publications using SerpAPI.")
    parser.add_argument("user_id", help="Google Scholar user ID")
    args = parser.parse_args()
    main(args.user_id)
