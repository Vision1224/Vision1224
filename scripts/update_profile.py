"""Refresh the verified public-projects block in README.md.

Lightweight equivalent of profile-README automation: only repositories listed
in FEATURED are shown, each with the status it has been checked against. The
script reads public metadata from the GitHub REST API and rewrites the block
between the PROJECTS markers. It never changes status labels or descriptions
that it cannot verify.

Standard library only. Set GITHUB_TOKEN to raise the API rate limit (optional).
"""

import json
import os
import re
import sys
import urllib.request
from datetime import datetime

OWNER = "Vision1224"
README = os.path.join(os.path.dirname(__file__), "..", "README.md")
START, END = "<!-- PROJECTS:START -->", "<!-- PROJECTS:END -->"

# repo name -> status label. Labels are curated by hand; only metadata is fetched.
FEATURED = {
    # name: (status label, fallback About text when the repo has no description; taken from its README)
    "ConnectFour": ("Original (Java, OOP)", "Java Connect Four built around OOP and game logic"),
    "Blackjack": ("Original (Java, OOP)", "Terminal Blackjack built in Java with object-oriented design"),
    "Malloc": ("Original (C, memory allocator)", "Custom memory allocator in C simulating low-level memory management"),
    "loan_approval_predictor": ("Demo (Flask + ML model)", "Flask API serving a simple machine-learning loan-approval model"),
    "docker-fundamentals": ("Learning repo (fork)", "Docker fundamentals practice"),
    "azure-devops-aks-kubernetes-terraform-pipeline": ("Learning repo (fork)", "AKS cluster provisioning with Azure DevOps pipelines"),
}

def fetch_repo(name):
    req = urllib.request.Request(
        f"https://api.github.com/repos/{OWNER}/{name}",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "profile-updater"},
    )
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.load(resp)


def render_block():
    rows = ["| Project | Status | About | Last push |", "| --- | --- | --- | --- |"]
    for name, (status, fallback) in FEATURED.items():
        try:
            repo = fetch_repo(name)
        except Exception as exc:  # keep the previous block if the API is unavailable
            print(f"warning: could not fetch {name}: {exc}", file=sys.stderr)
            return None
        if repo.get("private") or repo.get("archived"):
            print(f"skip {name}: private or archived", file=sys.stderr)
            continue
        desc = ((repo.get("description") or "").strip() or fallback).replace("|", "/")
        pushed = datetime.strptime(repo["pushed_at"], "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d")
        rows.append(f"| [**{name}**]({repo['html_url']}) | {status} | {desc} | {pushed} |")
    return "\n".join(rows)


def main():
    block = render_block()
    if block is None:
        return 0  # leave README unchanged on transient API failure
    with open(README, encoding="utf-8") as fh:
        text = fh.read()
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
    if not pattern.search(text):
        print("markers not found in README.md", file=sys.stderr)
        return 1
    new = pattern.sub(f"{START}\n{block}\n{END}", text, count=1)
    if new != text:
        with open(README, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(new)
        print("README projects block updated")
    else:
        print("no changes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
