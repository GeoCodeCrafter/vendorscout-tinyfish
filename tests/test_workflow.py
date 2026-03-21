import unittest

from workflow import build_goal_prompt, normalize_result_payload, normalize_vendor_list, vendor_name_from_url


class WorkflowTests(unittest.TestCase):
    def test_normalize_vendor_list_deduplicates_and_adds_scheme(self) -> None:
        vendors = normalize_vendor_list("example.com\nhttps://example.com\nstore.test")
        self.assertEqual(vendors, ["https://example.com", "https://store.test"])

    def test_vendor_name_from_url(self) -> None:
        self.assertEqual(vendor_name_from_url("https://www.bestbuy.com"), "Bestbuy")

    def test_build_goal_prompt_mentions_product_and_schema(self) -> None:
        prompt = build_goal_prompt("Sony WH-1000XM5", "https://example.com", "Prefer in-stock only")
        self.assertIn("Sony WH-1000XM5", prompt)
        self.assertIn("Return JSON only", prompt)
        self.assertIn("Prefer in-stock only", prompt)

    def test_normalize_result_payload_accepts_json_string(self) -> None:
        payload = normalize_result_payload('{"price":"$299","confidence":"high"}')
        self.assertEqual(payload["price"], "$299")
        self.assertEqual(payload["confidence"], "high")


if __name__ == "__main__":
    unittest.main()
