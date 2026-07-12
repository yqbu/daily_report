import ast
import unittest
from pathlib import Path


class DependencyBoundaryTests(unittest.TestCase):
    def test_storage_layer_does_not_import_service_layer(self) -> None:
        storage_root = Path("src/daily_report/storage")
        offenders: list[str] = []

        for path in storage_root.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                module = None
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.startswith("daily_report.service"):
                            module = alias.name
                            break
                elif isinstance(node, ast.ImportFrom):
                    module = node.module

                if module and module.startswith("daily_report.service"):
                    offenders.append(f"{path.as_posix()} imports {module}")

        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
