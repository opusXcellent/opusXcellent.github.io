import requests
import json
import base64
import os
from html.parser import HTMLParser

class MLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.fed = []

    def handle_data(self, d):
        self.fed.append(d)

    def get_data(self):
        return ''.join(self.fed)

def strip_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()

# === CONFIGURATION ===
DISQUS_API_KEY = os.getenv('DISQUS_API_KEY')
DISQUS_FORUM = 'champsfilmarchive'

GITHUB_REPO = 'opusXcellent/champsfilmarchive.net'
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
GITHUB_FILE_PATH = 'shared/latest_disqus_comments.json'
COMMIT_MESSAGE = 'Update latest Disqus comments'

# === STEP 1: Fetch Latest Comments ===
def fetch_latest_comments(limit=10):
    url = f"https://disqus.com/api/3.0/posts/list.json"
    params = {
        "api_key": DISQUS_API_KEY,
        "forum": DISQUS_FORUM,
        "limit": limit,
        "order": "desc"
    }
    response = requests.get(url, params=params)
    return response.json().get('response', [])

# === STEP 2: Enrich with Thread Info ===
def enrich_comments(comments):
    enriched = []
    for comment in comments:
        thread_id = comment['thread']
        thread_details = fetch_thread_details(thread_id)
        enriched.append({
            "author": comment['author']['name'],
            "message": strip_tags(comment['message']),
            "created_at": comment['createdAt'],
            "thread_id": thread_id,
            "thread_identifier": thread_details.get('identifiers', [''])[0],
            "thread_title": thread_details.get('title', ''),
            "thread_url": thread_details.get('link', '')
        })
    return enriched

def fetch_thread_details(thread_id):
    url = f"https://disqus.com/api/3.0/threads/details.json"
    params = {
        "api_key": DISQUS_API_KEY,
        "thread": thread_id
    }
    response = requests.get(url, params=params)
    return response.json().get('response', {})

# === STEP 3: Write to local JSON ===
def save_to_json(data, filename='latest_disqus_comments.json'):
    with open(filename, 'w') as f:
        json.dump({"comments": data}, f, indent=2)

# === STEP 4: Upload JSON to GitHub ===
def upload_to_github(file_path, repo, path_in_repo, token, commit_message):
    with open(file_path, 'rb') as file:
        content = base64.b64encode(file.read()).decode('utf-8')

    api_url = f'https://api.github.com/repos/{repo}/contents/{path_in_repo}'
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json',
    }

    # Check if file exists to get SHA
    get_resp = requests.get(api_url, headers=headers)
    sha = get_resp.json().get('sha') if get_resp.status_code == 200 else None

    data = {
        'message': commit_message,
        'content': content,
        'branch': 'main'
    }
    if sha:
        data['sha'] = sha

    response = requests.put(api_url, headers=headers, json=data)
    if response.status_code in [200, 201]:
        print('✅ Upload successful!')
    else:
        print('❌ Upload failed:', response.json())

# === MAIN EXECUTION ===
if __name__ == '__main__':
    comments = fetch_latest_comments(limit=10)
    enriched = enrich_comments(comments)
    save_to_json(enriched, 'latest_disqus_comments.json')
    upload_to_github(
        file_path='latest_disqus_comments.json',
        repo=GITHUB_REPO,
        path_in_repo=GITHUB_FILE_PATH,
        token=GITHUB_TOKEN,
        commit_message=COMMIT_MESSAGE
    )
