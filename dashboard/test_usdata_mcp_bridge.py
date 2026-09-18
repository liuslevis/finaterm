import unittest

from usdata_mcp_bridge import requires_refresh


class RequiresRefreshTests(unittest.TestCase):
    def test_refreshes_any_stale_series(self) -> None:
        payload = {
            "ok": True,
            "data": {
                "indicator_id": "treasury_10y_2y_spread",
                "is_stale": True,
            },
        }

        self.assertTrue(requires_refresh(payload))

    def test_keeps_fresh_series(self) -> None:
        payload = {
            "ok": True,
            "data": {
                "indicator_id": "treasury_10y_2y_spread",
                "is_stale": False,
            },
        }

        self.assertFalse(requires_refresh(payload))

    def test_ignores_error_payload(self) -> None:
        self.assertFalse(requires_refresh({"ok": False, "error": {}}))


if __name__ == "__main__":
    unittest.main()
