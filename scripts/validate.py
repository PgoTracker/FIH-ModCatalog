#!/usr/bin/env python3
"""
Valida mods.json: formato, valores permitidos, repos repetidos y que cada repo tenga una release instalable.
En un PR, además comprueba que solo los moderadores de speedrun cambien las reglas de speedrun.

Variables de entorno (las pone el workflow):
  GITHUB_TOKEN  token para consultar releases sin agotar el límite de la API
  BASE_REF      commit base del PR; sin ella se valida todo el archivo (push a main)
  PR_AUTHOR     usuario que abrió el PR
"""
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request

# Lo que el manager sabe mostrar: un valor nuevo aquí necesita también una versión nueva del manager.
CATEGORIES = {"cosmetic", "graphics", "practice", "challenge", "multiplayer", "creation"}
ICONS = {"edit", "timer", "palette", "flight", "person", "bolt", "link", "visibility", "translate", "camera",
         "chat", "image", "lock", "videocam", "brush", "sparkle", "brightness", "hook", "hanger", "tag"}
LANGUAGES = {"en", "es", "fr", "ru", "pl", "ar", "zh", "ko"}

MOD_KEYS = {"repo", "title", "author", "category", "icon", "explore", "speedrun", "description"}
REQUIRED = {"repo", "title", "author", "category", "icon", "description"}
REPO_RE = re.compile(r"^[A-Za-z0-9-]+/[A-Za-z0-9._-]+$")

errors = []


def error(where, message):
    errors.append(f"{where}: {message}")


def check_localized(where, value):
    if not isinstance(value, dict) or not value:
        error(where, "must be an object of language -> text")
        return
    if "en" not in value:
        error(where, "needs at least the English text (\"en\")")
    for lang, text in value.items():
        if lang not in LANGUAGES:
            error(where, f"unknown language \"{lang}\" (use {', '.join(sorted(LANGUAGES))})")
        if not isinstance(text, str) or not text.strip():
            error(f"{where}.{lang}", "must be a non-empty text")


def check_mod(index, mod):
    where = f"mods[{index}]"
    if not isinstance(mod, dict):
        error(where, "must be an object")
        return
    where = f"mods[{index}] ({mod.get('repo', '?')})"
    for key in REQUIRED - mod.keys():
        error(where, f"missing \"{key}\"")
    for key in mod.keys() - MOD_KEYS:
        error(where, f"unknown field \"{key}\"")

    repo = mod.get("repo")
    if not isinstance(repo, str) or not REPO_RE.match(repo):
        error(where, "\"repo\" must be \"owner/name\"")
    for key in ("title", "author"):
        if key in mod and (not isinstance(mod[key], str) or not mod[key].strip()):
            error(where, f"\"{key}\" must be a non-empty text")
    if "category" in mod and mod["category"] not in CATEGORIES:
        error(where, f"\"category\" must be one of {', '.join(sorted(CATEGORIES))}")
    if "icon" in mod and mod["icon"] not in ICONS:
        error(where, f"\"icon\" must be one of {', '.join(sorted(ICONS))}")
    if "explore" in mod and not isinstance(mod["explore"], bool):
        error(where, "\"explore\" must be true or false")
    if "description" in mod:
        check_localized(f"{where}.description", mod["description"])

    rule = mod.get("speedrun")
    if rule is not None:
        if not isinstance(rule, dict) or not isinstance(rule.get("allowed"), bool):
            error(f"{where}.speedrun", "must be {\"allowed\": true|false} with an optional \"note\"")
        else:
            for key in rule.keys() - {"allowed", "note"}:
                error(f"{where}.speedrun", f"unknown field \"{key}\"")
            if "note" in rule:
                check_localized(f"{where}.speedrun.note", rule["note"])
    if mod.get("explore") is False and rule is None:
        error(where, "a mod hidden from Explore (\"explore\": false) has to be in the Speedrun tab")


def github(url):
    request = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "FIH-ModCatalog"})
    if os.environ.get("GITHUB_TOKEN"):
        request.add_header("Authorization", f"Bearer {os.environ['GITHUB_TOKEN']}")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def check_release(repo):
    # Igual que el manager: la última release estable o, si solo hay prereleases, la más reciente.
    release = github(f"https://api.github.com/repos/{repo}/releases/latest")
    if release is None:
        releases = github(f"https://api.github.com/repos/{repo}/releases?per_page=1")
        if releases is None:
            error(repo, "repository not found (it has to be public)")
            return
        release = releases[0] if releases else None
    if release is None:
        error(repo, "has no releases: publish one with a .zip or .dll")
        return
    names = [a["name"].lower() for a in release.get("assets", [])]
    if not any(n.endswith(".zip") or n.endswith(".dll") for n in names):
        error(repo, f"release {release['tag_name']} has no .zip or .dll the manager can install")


def git_show(ref, path):
    result = subprocess.run(["git", "show", f"{ref}:{path}"], capture_output=True, text=True, encoding="utf-8")
    return result.stdout if result.returncode == 0 else None


def main():
    try:
        with open("mods.json", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"mods.json is not valid JSON: {e}")
        return 1

    if not isinstance(data, dict) or data.get("version") != 1 or not isinstance(data.get("mods"), list):
        print("mods.json must be {\"version\": 1, \"mods\": [...]}")
        return 1

    mods = data["mods"]
    for i, mod in enumerate(mods):
        check_mod(i, mod)

    seen = {}
    for mod in mods:
        repo = str(mod.get("repo", "")).lower() if isinstance(mod, dict) else ""
        if repo in seen:
            error(mod["repo"], "is listed twice")
        seen[repo] = mod

    # En un PR solo se consultan los repos nuevos o cambiados; en main, todos.
    base_ref = os.environ.get("BASE_REF")
    base_mods = {}
    if base_ref:
        base_text = git_show(base_ref, "mods.json")
        if base_text:
            base_mods = {m["repo"].lower(): m for m in json.loads(base_text)["mods"]}

    for repo, mod in seen.items():
        if REPO_RE.match(str(mod.get("repo", ""))) and (not base_ref or base_mods.get(repo) != mod):
            check_release(mod["repo"])

    if base_ref:
        # La lista de moderadores se lee de la rama base: un PR no puede añadirse a sí mismo.
        moderators_text = git_show(base_ref, ".github/speedrun-moderators.txt") or ""
        moderators = {line.strip().lower() for line in moderators_text.splitlines() if line.strip() and not line.startswith("#")}
        author = os.environ.get("PR_AUTHOR", "").lower()
        if author not in moderators:
            for repo in seen.keys() | base_mods.keys():
                before = base_mods.get(repo, {}).get("speedrun")
                after = seen.get(repo, {}).get("speedrun")
                if before != after:
                    error(seen.get(repo, base_mods.get(repo))["repo"],
                          "only speedrun moderators can add or change \"speedrun\" (see .github/speedrun-moderators.txt)")

    if errors:
        print("mods.json has problems:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print(f"mods.json OK: {len(mods)} mods")
    return 0


if __name__ == "__main__":
    sys.exit(main())
