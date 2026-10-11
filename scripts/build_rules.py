#!/usr/bin/env python3
"""Convert the maintained Loon rule source into native Mihomo classical providers."""
from __future__ import annotations

import re
from pathlib import Path

SOURCE = Path("/root/hermes-workspace/loon-rules/rules")
DEST = Path(__file__).resolve().parents[1] / "rules"
SUPPORTED = {"DOMAIN", "DOMAIN-SUFFIX", "DOMAIN-KEYWORD", "IP-CIDR", "IP-CIDR6"}


def convert_line(line: str) -> str | None:
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    parts = [part.strip() for part in line.split(",")]
    kind = parts[0].upper()
    if kind not in SUPPORTED or len(parts) < 2:
        return None
    value = parts[1].split(" @", 1)[0].strip()
    if not value or any(c in value for c in "*? "):
        raise ValueError(f"invalid rule payload: {line}")
    if kind.startswith("IP-CIDR"):
        import ipaddress
        ipaddress.ip_network(value, strict=False)
    elif kind != "DOMAIN-KEYWORD":
        if not re.fullmatch(r"[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*", value):
            raise ValueError(f"invalid domain payload: {line}")
        value = value.lower()
    return f"{kind},{value}"


def build() -> dict[str, int]:
    if not SOURCE.is_dir():
        raise FileNotFoundError(f"source rules directory not found: {SOURCE}")
    sources = sorted(SOURCE.glob("*.list"))
    if not sources:
        raise RuntimeError("no Loon .list source files found")
    DEST.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    for src in sources:
        rules = {rule for line in src.read_text(encoding="utf-8").splitlines()
                 if (rule := convert_line(line)) is not None}
        if src.stem != "STUN":
            rules.discard("DOMAIN-KEYWORD,stun")
        if not rules:
            raise RuntimeError(f"refusing to publish empty provider: {src.name}")
        payload = "\n".join(f"  - {rule}" for rule in sorted(rules))
        out = DEST / f"{src.stem}.yaml"
        out.write_text("# Generated from J606y/loon-rules; do not edit by hand.\n"
                       "payload:\n" + payload + "\n", encoding="utf-8")
        counts[src.stem] = len(rules)
    return counts


if __name__ == "__main__":
    for name, count in build().items():
        print(f"{name}: {count}")
