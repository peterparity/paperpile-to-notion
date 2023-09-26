import requests


NOTION_API_BASE_URL = "https://api.notion.com/v1"
CHAR_LIMIT=2000
TIMEOUT=60

def retry_request(url, total=4, status_forcelist=[429, 500, 502, 503, 504], **kwargs):
    # Make number of requests required
    for _ in range(total):
        try:
            response = requests.get(url, **kwargs)
            if response.status_code in status_forcelist:
                # Retry request 
                continue
            return response
        except requests.exceptions.ConnectionError:
            pass
    return None


def get_headers(notion_token):
    return {
        "Accept": "application/json",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {notion_token}",
    }


def query_db(db_id, headers=None):
    url = f"{NOTION_API_BASE_URL}/databases/{db_id}/query"
    payload = {"page_size": 100}
    response = {"has_more": True}

    pages = []

    while response["has_more"]:
        response = requests.post(url, json=payload, headers=headers, timeout=TIMEOUT).json()
        pages += response["results"]
        payload["start_cursor"] = response["next_cursor"]

    pages = [p for p in pages if p['archived'] is False]

    return pages


def update_page(db_id, properties, update_page_id=None, headers=None):
    payload = {
        "parent": {
            "database_id": db_id,
        },
        "properties": properties,
    }

    if update_page_id is not None:
        url = f"{NOTION_API_BASE_URL}/pages/{update_page_id}"
        response = requests.patch(url, json=payload, headers=headers, timeout=TIMEOUT)
    else:
        url = f"{NOTION_API_BASE_URL}/pages"
        response = requests.post(url, json=payload, headers=headers, timeout=TIMEOUT)

    return response.ok, response.text


def archive_page(page_id, headers=None):
    payload = {
        "archived": True
    }
    url = f"{NOTION_API_BASE_URL}/pages/{page_id}"
    response = requests.patch(url, json=payload, headers=headers, timeout=TIMEOUT)
    return response.ok, response.text


def is_blank_page(page_id, headers=None):
    url = f"{NOTION_API_BASE_URL}/blocks/{page_id}/children"
    response = retry_request(url, headers=headers, timeout=TIMEOUT).json()
    return len(response['results']) == 0


def get_property(page, prop_name, prop_type):
    p = page["properties"][prop_name]
    if prop_type == "title":
        content = p["title"][0]["text"]["content"]
    elif prop_type == "rich_text":
        content = p["rich_text"][0]["text"]["content"]
    elif prop_type == "number":
        content = p["number"]
    elif prop_type == "url":
        content = p["url"]
    elif prop_type == "multi_select":
        content = ";".join(tag['name'] for tag in p["multi_select"])
    else:
        content = ""
    return content


def property_to_value(property_type, content):
    if property_type == "title":
        return {
            "title": [{
                "text": { "content": content }
            }]
        }
    elif property_type == "rich_text":
        return {
            "rich_text": [
                {
                    "text": {"content": content[:CHAR_LIMIT]},
                    "type": "text",
                }
            ]
        }
    elif property_type == 'multi_select':
        if content == "":
            tags = []
        else:
            tags = content.split(";")
        return {
            "multi_select": [
                {
                    "name": tag
                }
                for tag in tags
            ]
        }
    elif property_type == "url":
        if content == "":
            content = None
        return {property_type: content}
    return {property_type: content}
