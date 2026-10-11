import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_rules


class RuleConversionTests(unittest.TestCase):
    def test_supported_domain_rule(self):
        self.assertEqual(build_rules.convert_line("DOMAIN-SUFFIX,Example.COM,Proxy"),
                         "DOMAIN-SUFFIX,example.com")

    def test_strip_ad_annotation(self):
        self.assertEqual(build_rules.convert_line("DOMAIN,ads.example @ads,REJECT"),
                         "DOMAIN,ads.example")

    def test_drop_client_only_rules(self):
        self.assertIsNone(build_rules.convert_line("IP-ASN,64500,Proxy"))
        self.assertIsNone(build_rules.convert_line("AND,((NETWORK,UDP)),REJECT"))
        self.assertIsNone(build_rules.convert_line("GEOIP,CN,DIRECT"))

    def test_reject_invalid_domain(self):
        with self.assertRaises(ValueError):
            build_rules.convert_line("DOMAIN,*.example.com,DIRECT")

    def test_reject_invalid_network(self):
        with self.assertRaises(ValueError):
            build_rules.convert_line("IP-CIDR,999.1.1.1/24,DIRECT")

    def test_build_providers_and_stun(self):
        counts = build_rules.build()
        self.assertEqual(len(counts), 25)
        self.assertTrue(all(count > 0 for count in counts.values()))
        stun = (ROOT / "rules" / "STUN.yaml").read_text(encoding="utf-8")
        self.assertIn("  - DOMAIN-KEYWORD,stun", stun)
        self.assertIn("  - DOMAIN-SUFFIX,stun.l.google.com", stun)
        self.assertNotIn("DEST-PORT", stun)
        ai = (ROOT / "rules" / "AI.yaml").read_text(encoding="utf-8")
        self.assertNotIn("DOMAIN-KEYWORD,stun", ai)
        for path in (ROOT / "rules").glob("*.yaml"):
            lines = path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(lines[1], "payload:")
            self.assertGreater(len(lines), 2)
            self.assertTrue(all(line.startswith("  - ") for line in lines[2:]))


if __name__ == "__main__":
    unittest.main()
