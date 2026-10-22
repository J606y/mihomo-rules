#!/usr/bin/env python3
"""Mihomo 自建全量规则集自动生成器
从权威上游 (v2fly & MetaCubeX) 抓取并清洗，结合定制补充配置，直接生成 Mihomo Classical 规则集。
脱离 Loon 依赖，完全独立维护。
"""
from __future__ import annotations
import json
import re
import ssl
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RULES_DIR = ROOT / "rules"

# 抓取和汇聚定义
TARGETS = {
    "AI": {
        "v2": ["anthropic", "openai", "google-gemini"],
        "mc": ["anthropic", "openai", "google-gemini"],
        "extra": [
            "PROCESS-NAME,Claude.exe", "PROCESS-NAME,claude.exe",
            "PROCESS-NAME,ChatGPT.exe", "PROCESS-NAME,Cursor.exe",
            "DOMAIN-SUFFIX,cursor.com", "DOMAIN-SUFFIX,cursor.sh",
            "DOMAIN-SUFFIX,statsigapi.net", "DOMAIN-SUFFIX,featuregates.org",
            "DOMAIN-SUFFIX,sentry.io", "DOMAIN-SUFFIX,intercom.io",
            "DOMAIN-SUFFIX,intercomcdn.com", "DOMAIN-SUFFIX,intercomassets.com",
            "DOMAIN-SUFFIX,chat.com", "DOMAIN-SUFFIX,sora.com", "DOMAIN-SUFFIX,oaistatsig.com",
            "DOMAIN-SUFFIX,perplexity.ai", "DOMAIN-SUFFIX,aistudio.google.com",
            "DOMAIN-SUFFIX,generativelanguage.googleapis.com",
            "DOMAIN-SUFFIX,grok.com", "DOMAIN-SUFFIX,grokipedia.com", "DOMAIN-SUFFIX,x.ai",
            "DOMAIN,grok.x.com",
            "DOMAIN-KEYWORD,stun"
        ]
    },
    "Cloud": {
        "v2": ["amazon", "azure", "digitalocean", "oracle"],
        "mc": ["amazon", "azure", "oracle"],
        "extra": [
            "DOMAIN-SUFFIX,cloud.google.com", "DOMAIN-SUFFIX,googlecloud.com", "DOMAIN-SUFFIX,gcr.io",
            "DOMAIN-SUFFIX,appspot.com", "DOMAIN-SUFFIX,run.app", "DOMAIN-SUFFIX,cloudfunctions.net",
            "DOMAIN,compute.googleapis.com", "DOMAIN,storage.googleapis.com", "DOMAIN,container.googleapis.com",
            "DOMAIN,run.googleapis.com", "DOMAIN-SUFFIX,bandwagonhost.com", "DOMAIN-SUFFIX,bwh81.net",
            "DOMAIN-SUFFIX,bwh88.net", "DOMAIN-SUFFIX,bwh89.net", "DOMAIN-SUFFIX,bwh8.net",
            "DOMAIN-SUFFIX,vultr.com", "DOMAIN-SUFFIX,linode.com", "DOMAIN-SUFFIX,hetzner.com",
            "DOMAIN-SUFFIX,hetzner.cloud", "DOMAIN-SUFFIX,ovhcloud.com", "DOMAIN-SUFFIX,ovh.com",
            "DOMAIN-SUFFIX,kamatera.com", "DOMAIN-SUFFIX,upcloud.com", "DOMAIN-SUFFIX,scaleway.com"
        ]
    },
    "YouTube": {"v2": ["youtube"], "mc": ["youtube"]},
    "Netflix": {"v2": ["netflix"], "mc": ["netflix"]},
    "Spotify": {"v2": ["spotify"], "mc": ["spotify"]},
    "Telegram": {
        "v2": ["telegram"], "mc": ["telegram"],
        "extra": [
            "IP-CIDR,91.105.192.0/23", "IP-CIDR,91.108.4.0/22", "IP-CIDR,91.108.8.0/21",
            "IP-CIDR,91.108.16.0/21", "IP-CIDR,91.108.56.0/22", "IP-CIDR,95.161.64.0/20",
            "IP-CIDR,149.154.160.0/20", "IP-CIDR,185.76.151.0/24", "IP-CIDR6,2001:67c:4e8::/48",
            "IP-CIDR6,2001:b28:f23c::/47", "IP-CIDR6,2001:b28:f23f::/48", "IP-CIDR6,2a0a:f280::/32"
        ]
    },
    "Twitter": {"v2": ["twitter"], "mc": ["twitter"]},
    "Google": {"v2": ["google"], "mc": ["google"]},
    "Microsoft": {"v2": ["microsoft"], "mc": ["microsoft"]},
    "Apple": {"v2": ["apple"], "mc": ["apple"]},
    "GitHub": {"v2": ["github"], "mc": ["github"]},
    "Cloudflare": {"v2": ["cloudflare"], "mc": ["cloudflare"]},
    "Games": {
        "mc": ["category-games-!cn"],
        "extra": [
            "PROCESS-NAME,steam.exe", "PROCESS-NAME,EpicGamesLauncher.exe", "DOMAIN-SUFFIX,easy.ac"
        ]
    },
    "STUN": {
        "extra": [
            "DST-PORT,3478",
            "DST-PORT,5349",
            "DST-PORT,19302",
            "DOMAIN-KEYWORD,stun",
            "DOMAIN-SUFFIX,stun.cloudflare.com",
            "DOMAIN-SUFFIX,stun.l.google.com",
            "DOMAIN-SUFFIX,stun.services.mozilla.com"
        ]
    },
    "ClaudeUDP": {
        "extra": [
            "AND,((NETWORK,UDP),(PROCESS-NAME,Claude.exe))",
            "AND,((NETWORK,UDP),(PROCESS-NAME,claude.exe))",
            "AND,((NETWORK,UDP),(DOMAIN-SUFFIX,anthropic.com))",
            "AND,((NETWORK,UDP),(DOMAIN-SUFFIX,anthropic.ai))",
            "AND,((NETWORK,UDP),(DOMAIN-SUFFIX,claude.ai))",
            "AND,((NETWORK,UDP),(DOMAIN-SUFFIX,claude.com))",
            "AND,((NETWORK,UDP),(DOMAIN-SUFFIX,claudeusercontent.com))",
            "AND,((NETWORK,UDP),(DOMAIN-SUFFIX,claude-code.com))",
            "AND,((NETWORK,UDP),(DOMAIN-SUFFIX,claude.dev))",
            "AND,((NETWORK,UDP),(DOMAIN-SUFFIX,clau.de))",
            "AND,((NETWORK,UDP),(DOMAIN-SUFFIX,claudemcpclient.com))",
            "AND,((NETWORK,UDP),(DOMAIN-SUFFIX,claudemcpcontent.com))"
        ]
    }
}

headers = {"User-Agent": "Mozilla/5.0 (compatible; MihomoRulesBuilder/1.0)"}
ctx = ssl.create_default_context()

def fetch(url: str) -> str:
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=20, context=ctx) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception:
        return ""

def parse_rules(text: str) -> set[str]:
    rules = set()
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("- "):
            line = line[2:].strip().strip("'\"")
            if "," in line:
                parts = line.split(",")
                rules.add(f"{parts[0].strip()},{parts[1].strip()}")
                continue
        if line.startswith("full:"):
            rules.add(f"DOMAIN,{line[5:].strip()}")
        elif line.startswith("regexp:") or line.startswith("^") or line.startswith("include:"):
            continue
        else:
            val = line.split()[0].strip()
            if "." in val and not val.startswith("@"):
                rules.add(f"DOMAIN-SUFFIX,{val}")
    return rules

def build_single(item: tuple[str, dict]) -> tuple[str, int]:
    name, conf = item
    rules = set()

    for d in conf.get("extra", []):
        rules.add(d)

    for slug in conf.get("v2", []):
        url = f"https://raw.githubusercontent.com/v2fly/domain-list-community/master/data/{slug}"
        t = fetch(url)
        if t:
            rules |= parse_rules(t)

    for slug in conf.get("mc", []):
        url = f"https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/geo/geosite/classical/{slug}.yaml"
        t = fetch(url)
        if t:
            rules |= parse_rules(t)

    sorted_rules = sorted(list(rules))
    out_file = RULES_DIR / f"{name}.yaml"
    content = f"# Generated from authoritative upstreams (v2fly & MetaCubeX)\n# Category: {name}\npayload:\n"
    content += "".join(f"  - {json.dumps(r)}\n" for r in sorted_rules)
    out_file.write_text(content, encoding="utf-8")
    return name, len(sorted_rules)

def build_all() -> dict[str, int]:
    RULES_DIR.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=8) as ex:
        results = list(ex.map(build_single, TARGETS.items()))
    counts = {}
    for name, count in results:
        counts[name] = count
        print(f" -> {name:15}: {count:5d} rules compiled")
    return counts

if __name__ == "__main__":
    build_all()
