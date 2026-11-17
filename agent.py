"""WebScout: navigate a website and return the exact piece of information asked for."""
import json
import os
import re
import sys
from urllib.parse import urljoin, urldefrag, urlparse

import requests
from bs4 import BeautifulSoup

LLM_URL = os.getenv("LLM_URL", "http://localhost:8000/v1/chat/completions")
MODEL = os.getenv("LLM_MODEL", "Qwen/Qwen3-8B")
MAX_STEPS = int(os.getenv("MAX_STEPS", "8"))
MAX_PAGE_CHARS = 6000
MAX_LINKS = 40
HEADERS = {"User-Agent": "Mozilla/5.0 (WebScout research agent)"}

SYSTEM = """You are a web navigation agent. You are given a user question, the current page's
text and a numbered list of links on the same site. Reply with ONE JSON object only:
{"action": "answer", "answer": "<short exact answer>", "evidence": "<verbatim sentence copied from the page text>"}
{"action": "follow", "link": <number of the most promising link>}
{"action": "not_found"}
Rules: answer ONLY if the page text contains the answer. Give the specific value asked for,
not a summary. Evidence must be copied exactly from the page text. Never invent information."""


def fetch(url):
    r = requests.get(url, headers=HEADERS, timeout=15)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    host = urlparse(url).netloc
    links, seen = [], set()
    for a in soup.find_all("a", href=True):
        href = urldefrag(urljoin(url, a["href"]))[0]
        text = " ".join(a.get_text().split())[:80]
        if urlparse(href).scheme in ("http", "https") and urlparse(href).netloc == host \
                and href not in seen and href != url and text:
            seen.add(href)
            links.append((text, href))
    text = re.sub(r"\n\s*\n+", "\n", soup.get_text("\n"))
    return text.strip()[:MAX_PAGE_CHARS], links[:MAX_LINKS]


def llm(messages):
    body = {"model": MODEL, "messages": messages, "temperature": 0, "max_tokens": 400,
            "chat_template_kwargs": {"enable_thinking": False}}
    r = requests.post(LLM_URL, json=body, timeout=120)
    r.raise_for_status()
    out = r.json()["choices"][0]["message"]["content"]
    out = re.sub(r"<think>.*?</think>", "", out, flags=re.S)
    m = re.search(r"\{.*\}", out, re.S)
    try:
        return json.loads(m.group(0)) if m else {"action": "not_found"}
    except json.JSONDecodeError:
        return {"action": "not_found"}


def norm(s):
    return re.sub(r"\s+", " ", s).strip().lower()


def ask(start_url, question, max_steps=MAX_STEPS):
    url, visited, path, candidate = start_url, set(), [], None
    for _ in range(max_steps):
        visited.add(url)
        path.append(url)
        try:
            text, links = fetch(url)
        except Exception as e:  # noqa: BLE001
            return {"answer": None, "error": str(e), "path": path, "verified": False}
        link_list = "\n".join(f"{i}. {t} -> {h}" for i, (t, h) in enumerate(links))
        user = f"Question: {question}\n\nPAGE URL: {url}\nPAGE TEXT:\n{text}\n\nLINKS:\n{link_list}"
        if candidate:
            user += "\n\nNote: an earlier answer lacked verbatim evidence; look for a better one."
        decision = llm([{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}])

        if decision.get("action") == "answer" and decision.get("answer"):
            evidence = decision.get("evidence", "")
            verified = bool(evidence) and norm(evidence) in norm(text)
            result = {"answer": decision["answer"], "evidence": evidence,
                      "source_url": url, "verified": verified, "path": path}
            if verified:
                return result
            candidate = result
        elif decision.get("action") == "follow":
            try:
                nxt = links[int(decision["link"])][1]
            except (KeyError, ValueError, IndexError, TypeError):
                break
            if nxt in visited:
                break
            url = nxt
        else:
            break
    return candidate or {"answer": None, "source_url": None, "verified": False,
                         "path": path, "note": "not found"}


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit('usage: python agent.py <start_url> "<question>"')
    print(json.dumps(ask(sys.argv[1], sys.argv[2]), indent=2))
