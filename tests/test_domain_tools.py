import unittest


class DomainToolTests(unittest.TestCase):
    def test_category_helpers_are_available_from_domain_layer(self) -> None:
        from daily_report.domain.category import (
            infer_category_for_ai_prompt,
            infer_category_for_app,
            infer_category_for_browser,
        )

        self.assertEqual(infer_category_for_app("python.exe", "daily_report main.py"), "开发编码")
        self.assertEqual(
            infer_category_for_browser("FastAPI error", "https://example.test", False, None),
            "问题排查",
        )
        self.assertEqual(infer_category_for_ai_prompt("请帮我安装开发环境"), "系统配置")

    def test_sensitivity_helpers_are_available_from_domain_layer(self) -> None:
        from daily_report.domain.sensitivity import detect_sensitive_text, hash_text, make_preview

        is_sensitive, reason = detect_sensitive_text("Authorization: Bearer abcdefghijklmnopqrstuvwxyz")

        self.assertIs(is_sensitive, True)
        self.assertIn(reason, {"keyword:authorization", "bearer", "token"})
        self.assertEqual(make_preview("  hello\n\nworld  ", 20), "hello world")
        self.assertEqual(len(hash_text("hello")), 64)


if __name__ == "__main__":
    unittest.main()
