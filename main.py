import os
import re
import json
import time
import aiohttp
import asyncio
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

async def fetch_profile(username: str, api_key: str, strip_data: bool):
    start_time = time.monotonic()
    target_url = f"https://www.tiktok.com/@{username}"
    payload = {'api_key': api_key, 'url': target_url, 'country_code': 'us'}
    proxy_url = 'http://api.scraperapi.com'
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=90)) as session:
            async with session.get(proxy_url, params=payload) as response:
                if response.status != 200:
                    return None, f"Status {response.status}"
                html_content = await response.text()
        match = re.search(r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__" type="application/json">(.*?)</script>', html_content)
        if not match:
            return None, "Data not found in page"
        data_json = json.loads(match.group(1))
        user_info = data_json.get("__DEFAULT_SCOPE__", {}).get("webapp.user-detail", {}).get("userInfo", {})
        author_info = user_info.get("user", {})
        author_stats = user_info.get("stats", {})
        if not author_info or not author_stats:
            return None, "Incomplete user data"
        if strip_data:
            keys_to_remove_author = {"ftc", "relation", "openFavorite", "commentSetting", "commerceUserInfo", "duetSetting", "stitchSetting", "secret", "isADVirtual", "downloadSetting", "profileTab", "followingVisibility", "recommendReason", "nowInvitationCardUrl", "isEmbedBanned", "canExpPlaylist", "profileEmbedPermission", "eventList", "suggestAccountBind", "isOrganization", "UserStoryStatus", "secUid", "shortId"}
            keys_to_remove_stats = {"diggCount"}
            for key in keys_to_remove_author:
                author_info.pop(key, None)
            for key in keys_to_remove_stats:
                author_stats.pop(key, None)
        if 'signature' in author_info and isinstance(author_info['signature'], str):
            author_info['signature'] = author_info['signature'].replace('\n', ' ')
        data = {"author_details": author_info, "stats": author_stats, "is_live": bool(author_info.get("roomId"))}
        return data, None
    except Exception as e:
        return None, str(e)

@app.get("/{username}", response_class=HTMLResponse)
async def get_profile(username: str):
    config_path = os.path.join("data", "config.json")
    if not os.path.exists(config_path):
        return HTMLResponse(content="config.json not found", status_code=500)
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    api_key = config.get("api_key")
    strip_data = config.get("strip_extra_data", False)
    if not api_key or "YOUR_API_KEY" in api_key:
        return HTMLResponse(content="Invalid API key", status_code=500)
    data, error = await fetch_profile(username, api_key, strip_data)
    if error:
        return HTMLResponse(content=f"Error: {error}", status_code=400)
    pretty_json = json.dumps(data, indent=4, ensure_ascii=False)
    html = f'''<html><head><meta name="color-scheme" content="light dark"><meta charset="utf-8"></head><body><pre>{pretty_json}</pre><div class="json-formatter-container"></div></body></html>'''
    return HTMLResponse(content=html)
