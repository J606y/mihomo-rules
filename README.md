# J606y Mihomo Rules

自维护的 Mihomo 规则集订阅库。源数据继承自本地 Loon 规则构建流程：v2fly 社区数据与 MetaCubeX 官方规则交叉汇总、清洗后转换为 Mihomo `classical` provider；不依赖第三方规则聚合站。

## 订阅

Base URL：`https://raw.githubusercontent.com/J606y/mihomo-rules/main/rules/`

将文件名（不含扩展名）用作 provider 名称，例如：

```yaml
rule-providers:
  AI:
    type: http
    behavior: classical
    format: yaml
    url: https://raw.githubusercontent.com/J606y/mihomo-rules/main/rules/AI.yaml
    path: ./ruleset/AI.yaml
    interval: 86400
rules:
  - RULE-SET,AI,🤖 AI
```

仓库 `rules/` 下每个 YAML 文件均为独立 provider，涵盖 AI、Claude、OpenAI、Gemini、YouTube、Netflix、Spotify、Telegram、Twitter、TikTok、Reddit、WhatsApp、Pixiv、Steam、PayPal、Google、GitHub、Cloudflare、Microsoft、Apple、Bilibili、WeChat、AdBlock、China 与 STUN。

## WebRTC / STUN

`STUN.yaml` 是域名规则集，策略应设为 `REJECT`，并置于可能命中的其他域名规则之前。规则集本身不包含按端口过滤的规则；Mihomo 规则提供器不支持把 Loon 的 `AND,((PROTOCOL,UDP),(DEST-PORT,...))` 原样转换为 classical 条目。如需封锁 STUN 常用 UDP 端口 3478/5349，应在本地 `rules:` 中将客户端支持的端口规则置于其他分流规则之前。仅订阅域名集不能证明所有 WebRTC 流量均已阻断。

## 生成与校验

```sh
python3 scripts/build_rules.py
python3 -m unittest discover -s tests -v
```

生成器只输出 Mihomo classical 支持的 DOMAIN、DOMAIN-SUFFIX、DOMAIN-KEYWORD、IP-CIDR、IP-CIDR6 条目。Loon 特有的进程名、IP-ASN、GEOIP 和策略字段会被排除，不会伪装成 Mihomo provider。
