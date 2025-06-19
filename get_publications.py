import argparse
import json
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/90.0.4430.85 Safari/537.36"
}

BASE_URL = "https://scholar.google.com"

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

def get_citation_ids(user_id):
    url = f"{BASE_URL}/citations?user={user_id}&hl=en&cstart=1&pagesize=1000"
    response = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(response.text, "html.parser")
    citation_links = soup.find_all("a", class_="gsc_a_at")
    citation_ids = [
        a["href"].split("citation_for_view=")[-1]
        for a in citation_links if "citation_for_view=" in a["href"]
    ]
    return citation_ids

def parse_citation(user_id, citation_id):
    url = f"{BASE_URL}/citations?view_op=view_citation&hl=en&user={user_id}&cstart=1&pagesize=1000&citation_for_view={citation_id}"
    response = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(response.text, "html.parser")

    table = soup.find("div", id="gsc_oci_table")
    result = {}

    if not table:
        return result

    rows = table.find_all("div", class_="gs_scl")
    for row in rows:
        field_div = row.find("div", class_="gsc_oci_field")
        value_div = row.find("div", class_="gsc_oci_value")
        if field_div and value_div:
            key = field_div.text.strip()
            value = value_div.get_text(separator=" ", strip=True)
            result[key] = value
    return result

def main(user_id):
    print(f"Fetching citations for user: {user_id}")
    citation_ids = get_citation_ids(user_id)
    print(f"Found {len(citation_ids)} citations.")

    all_data = []
    for i, citation_id in enumerate(citation_ids, 1):
        print(f"[{i}/{len(citation_ids)}] Processing citation: {citation_id}")
        citation_data = parse_citation(user_id, citation_id)
        if citation_data:
            all_data.append(citation_data)
        time.sleep(1)  # Be polite with Google Scholar

    journal_entries = []
    other_entries = []

    for entry in all_data:
        entry["__parsed_date__"] = parse_date(entry.get("Publication date", ""))
        if "Journal" in entry:
            journal_entries.append(entry)
        else:
            other_entries.append(entry)

    journal_entries.sort(key=lambda x: x["__parsed_date__"])
    other_entries.sort(key=lambda x: x["__parsed_date__"])

    # Remove temporary key before saving
    for e in journal_entries + other_entries:
        e.pop("__parsed_date__", None)

    final_json = {
        "Journal": journal_entries,
        "others": other_entries
    }

    output_filename = f"scholar_data_{user_id}.json"
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(final_json, f, indent=2, ensure_ascii=False)

    print(f"Saved sorted data to {output_filename}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape Google Scholar user publications.")
    parser.add_argument("user_id", help="Google Scholar user ID")
    args = parser.parse_args()
    main(args.user_id)

