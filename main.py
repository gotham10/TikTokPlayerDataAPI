import os
import re
import json
import time
import aiohttp
import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

API_KEY = "f9626c4887b61dba7534d071d389bfaa"
STRIP_EXTRA_DATA = True

async def fetch_profile(username: str):
    start_time = time.monotonic()
    target_url = f"https://www.tiktok.com/@{username}"
    payload = {'api_key': API_KEY, 'url': target_url, 'country_code': 'us'}
    proxy_url = 'http://api.scraperapi.com'
    
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=90)) as session:
            async with session.get(proxy_url, params=payload) as response:
                if response.status != 200:
                    return None, f"Proxy Error: Status {response.status}"
                html_content = await response.text()

        match = re.search(r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__" type="application/json">(.*?)</script>', html_content)
        if not match:
            return None, "Could not find user data in the page response. The page structure may have changed."

        data_json = json.loads(match.group(1))
        user_info_scope = data_json.get("__DEFAULT_SCOPE__", {}).get("webapp.user-detail", {})
        author_info = user_info_scope.get("userInfo", {}).get("user", {})
        author_stats = user_info_scope.get("userInfo", {}).get("stats", {})

        if not author_info or not author_stats:
            return None, "Incomplete user data found. The user may not exist or the API response is malformed."

        if STRIP_EXTRA_DATA:
            keys_to_remove_author = {
                "ftc", "relation", "openFavorite", "commentSetting", "commerceUserInfo", 
                "duetSetting", "stitchSetting", "secret", "isADVirtual", "downloadSetting",
                "profileTab", "followingVisibility", "recommendReason", "nowInvitationCardUrl",
                "isEmbedBanned", "canExpPlaylist", "profileEmbedPermission", "eventList",
                "suggestAccountBind", "isOrganization", "UserStoryStatus", "secUid", "shortId"
            }
            keys_to_remove_stats = {"diggCount"}
            
            for key in keys_to_remove_author:
                author_info.pop(key, None)
            for key in keys_to_remove_stats:
                author_stats.pop(key, None)

        if 'signature' in author_info and isinstance(author_info['signature'], str):
            author_info['signature'] = author_info['signature'].replace('\n', ' ')

        data = {
            "author_details": author_info,
            "stats": author_stats,
            "is_live": bool(author_info.get("roomId"))
        }
        return data, None
    except Exception as e:
        return None, f"An unexpected error occurred: {str(e)}"

@app.get("/{username}", response_class=HTMLResponse)
async def get_profile(username: str):
    if not API_KEY or "YOUR_API_KEY" in API_KEY:
        return HTMLResponse(content="Error: Server API key is not configured.", status_code=500)

    data, error = await fetch_profile(username)
    if error:
        return HTMLResponse(content=f"Error: {error}", status_code=400)

    pretty_json = json.dumps(data, indent=4, ensure_ascii=False)
    html_content = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="color-scheme" content="light dark">
        <title>Profile Data</title>
        <style>
            body {{ font-family: monospace; background-color: #1a1a1a; color: #f0f0f0; }}
            pre {{ white-space: pre-wrap; word-wrap: break-word; }}
        </style>
    </head>
    <body>
        <pre>{pretty_json}</pre>
    </body>
    </html>
    '''
    return HTMLResponse(content=html_content)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
