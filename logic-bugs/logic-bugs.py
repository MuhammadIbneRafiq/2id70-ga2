import os
import requests
import pandas as pd
from dotenv import load_dotenv
import time
import re
# 1. load the env varible
load_dotenv(override=True)
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")


def extract_version_from_body(body_text):
    """
    Find neo4j versions
    """
    if not body_text:
        return "No body_text"


    match = re.search(r'\b([45]\.\d+(\.\d+)?)\b', body_text)

    if match:
        return match.group(1)
    else:
        return "check manually"



def get_all_neo4j_bugs():
    print("Neo4j logic bugs collecting\n")

    url = "https://api.github.com/search/issues"
    search_query = 'repo:neo4j/neo4j is:issue label:bug "wrong result" OR "incorrect result" OR "WHERE clause"'

    all_issues = []
    page = 1

    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"Bearer {GITHUB_TOKEN.strip()}"
    }

    while True:
        print(f" {page}page request...")
        params = {
            "q": search_query,
            "sort": "created",
            "order": "desc",
            "per_page": 100,
            "page": page
        }

        response = requests.get(url, headers=headers, params=params)

        if response.status_code != 200:
            print(f"error: {response.status_code}")
            break

        data = response.json()
        items = data.get("items", [])


        if not items:
            break

        for issue in items:
            body_content = issue.get('body', '')
            version = extract_version_from_body(body_content)
            all_issues.append({
                "Issue Number": f"#{issue['number']}",
                "Description": issue['title'],
                "Version": version,
                "Link": issue['html_url'],
                "Created At": issue['created_at']
            })

        time.sleep(1)


        page += 1

    df = pd.DataFrame(all_issues)
    return df

def groupby(df):
    df_grouped = df.groupby('Version').size().sort_values( ascending=False)

    return df_grouped


def df_to_excel(df: pd.DataFrame):
    if df is not None and not df.empty:
        df.to_excel("neo4j_bugs_with_version.xlsx", index=False)
        print(f"\n total {len(df)}saved successfully!")
    else:
        print("No data exist")


if __name__ == "__main__":
    df = get_all_neo4j_bugs()
    df_grouped = groupby(df)
    print(df.head(5))
    print(df_grouped.head(5))
    df_to_excel(df)
    # df_to_excel(df_grouped)

