import os
import re
import json
import time
import aiohttp
import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI(docs_url=None, redoc_url=None)

API_KEY = "f9626c4887b61dba7534d071d389bfaa"
STRIP_EXTRA_DATA = True

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>JSON Viewer</title>
<script src="https://cdn.tailwindcss.com"></script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Roboto+Mono&display=swap" rel="stylesheet">
<style>
body {{
    margin: 0;
    padding: 0;
    background-color: #111111;
    color: #f9fafb;
    font-family: 'Roboto Mono', monospace;
    height: 100vh;
    overflow: hidden;
}}
*::-webkit-scrollbar {{
    display: none;
}}
* {{
    scrollbar-width: none;
}}
.json-formatter-header {{
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    height: 24px;
    background-color: #3c3c3c;
    border-bottom: 1px solid #bbbbbb;
    z-index: 50;
    display: flex;
    align-items: center;
    font-size: 12px;
    padding-left: 0;
}}
#scrollArea {{
    position: absolute;
    top: 24px;
    bottom: 0;
    left: 0;
    right: 0;
    overflow-y: scroll;
    padding: 6px 8px;
}}
.pretty-print {{
    white-space: pre-wrap;
}}
.single-line {{
    white-space: pre-wrap;
    word-break: break-word;
}}
label[for="prettyPrintToggle"] {{
    margin: 0;
    padding-left: 4px;
}}
.toggle-container {{
    display: flex;
    align-items: center;
    margin-left: 6px;
}}
input[type="checkbox"] {{
    display: none;
}}
.toggle-box {{
    width: 13px;
    height: 13px;
    background-color: transparent;
    border: 1.5px solid #aaaaaa;
    border-radius: 3px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: border-color 0.2s ease;
}}
input[type="checkbox"]:not(:checked) + .toggle-box:hover {{
    border-color: #dddddd;
}}
input[type="checkbox"]:checked + .toggle-box {{
    background-color: #99c8ff;
    border: none;
}}
input[type="checkbox"]:checked + .toggle-box:hover {{
    background-color: #d1e6ff;
}}
.toggle-box svg {{
    width: 12px;
    height: 10px;
    fill: #3b3b3b;
    display: none;
    margin-left: -3px;
}}
input[type="checkbox"]:checked + .toggle-box svg {{
    display: block;
}}
</style>
</head>
<body>
<div class="json-formatter-header">
    <label for="prettyPrintToggle">Pretty-print</label>
    <div class="toggle-container">
        <input type="checkbox" id="prettyPrintToggle" checked>
        <label class="toggle-box" for="prettyPrintToggle">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 448 512">
                <path d="M438.6 105.4c12.5 12.5 12.5 32.8 0 45.3l-256 256c-12.5 12.5-32.8 12.5-45.3 0l-128-128c-12.5-12.5-12.5-32.8 0-45.3s32.8-12.5 45.3 0L160 338.7 393.4 105.4c12.5-12.5 32.8-12.5 45.3 0z"/>
            </svg>
        </label>
    </div>
</div>
<div id="scrollArea">
    <pre id="jsonContent" class="text-[13px] leading-snug"></pre>
</div>
<script>
const jsonData = {json_data};
const toggle = document.getElementById('prettyPrintToggle');
const contentEl = document.getElementById('jsonContent');

function updateView() {{
    const prettyString = JSON.stringify(jsonData, null, 2);
    const singleLineString = JSON.stringify(jsonData);
    if (toggle.checked) {{
        contentEl.textContent = prettyString;
        contentEl.classList.add('pretty-print');
        contentEl.classList.remove('single-line');
    }} else {{
        contentEl.textContent = singleLineString;
        contentEl.classList.add('single-line');
        contentEl.classList.remove('pretty-print');
    }}
}}
toggle.addEventListener('change', updateView);
updateView();
</script>
</body>
</html>
"""

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
            author_info['signature'] = author_info['signature'].replace('\\n', ' ')

        data = {
            "author_details": author_info,
            "stats": author_stats,
            "is_live": bool(author_info.get("roomId"))
        }
        return data, None
    except Exception as e:
        return None, f"An unexpected error occurred: {str(e)}"

@app.get("/", response_class=HTMLResponse)
async def read_root():
    instructions = {
        "api_info": {
            "status": "online",
            "usage": "To use this API, enter a TikTok username after the slash.",
            "example": "/thatsdemitri"
        }
    }
    html_content = HTML_TEMPLATE.format(json_data=json.dumps(instructions))
    return HTMLResponse(content=html_content)

@app.get("/{username}", response_class=HTMLResponse)
async def get_profile(username: str):
    if not API_KEY or "YOUR_API_KEY" in API_KEY:
        error_data = {"error": "Server API key is not configured."}
        html_content = HTML_TEMPLATE.format(json_data=json.dumps(error_data))
        return HTMLResponse(content=html_content, status_code=500)

    data, error = await fetch_profile(username)
    if error:
        error_data = {"error": error}
        html_content = HTML_TEMPLATE.format(json_data=json.dumps(error_data))
        return HTMLResponse(content=html_content, status_code=400)

    html_content = HTML_TEMPLATE.format(json_data=json.dumps(data, ensure_ascii=False))
    return HTMLResponse(content=html_content)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
