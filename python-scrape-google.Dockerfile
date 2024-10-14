FROM python:3.9-slim

WORKDIR /app

RUN pip install --no-cache-dir requests beautifulsoup4

RUN echo '#!/usr/bin/env python3\n\
import os\n\
import json\n\
import requests\n\
from bs4 import BeautifulSoup\n\
\n\
def search_google(query):\n\
    url = f"https://www.google.com/search?q={query}"\n\
    headers = {\n\
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"\n\
    }\n\
    response = requests.get(url, headers=headers)\n\
    soup = BeautifulSoup(response.text, "html.parser")\n\
    \n\
    results = soup.find_all("h3")\n\
    \n\
    for result in results:\n\
        print(result.get_text(strip=True))\n\
\n\
if __name__ == "__main__":\n\
    job_args = os.environ.get("JOB_ARGS", "{}")\n\
    args = json.loads(job_args)\n\
    query = args.get("query", "")\n\
    \n\
    if query:\n\
        search_google(query)\n\
' > /app/google_search.py

CMD ["python", "/app/google_search.py"]