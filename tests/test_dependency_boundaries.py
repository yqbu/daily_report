import ast
import json
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

    def test_javascript_packages_use_single_frontend_workspace(self) -> None:
        package = json.loads(Path("package.json").read_text(encoding="utf-8"))

        self.assertEqual(package.get("workspaces"), ["frontend"])
        self.assertFalse(Path("frontend/package-lock.json").exists())
        self.assertNotIn("@tauri-apps/api", package.get("dependencies", {}))
        self.assertIn("--workspace daily-report-web-ui", package["scripts"]["frontend:dev"])
        self.assertIn("--workspace daily-report-web-ui", package["scripts"]["frontend:build"])

    def test_frontend_has_no_legacy_desktop_adapters(self) -> None:
        self.assertFalse(Path("frontend/src/api/bridgeAdapters").exists())
        self.assertFalse(Path("frontend/src/api/mock.ts").exists())

        legacy_terms = ("PySide6", "QWebChannel", "webChannelTransport", "pyBridge")
        offenders: list[str] = []
        source_roots = (Path("frontend/src"), Path("src"), Path("src-tauri/src"))
        suffixes = {".py", ".rs", ".ts", ".vue"}

        for source_root in source_roots:
            for path in source_root.rglob("*"):
                if not path.is_file() or path.suffix not in suffixes:
                    continue
                content = path.read_text(encoding="utf-8")
                for term in legacy_terms:
                    if term in content:
                        offenders.append(f"{path.as_posix()} contains {term}")

        self.assertEqual(offenders, [])

    def test_python_package_does_not_bundle_tauri_frontend(self) -> None:
        pyproject = Path("pyproject.toml").read_text(encoding="utf-8")

        self.assertNotIn("share/daily-report/frontend/dist", pyproject)

    def test_runtime_loading_layer_stays_below_sidebar_navigation(self) -> None:
        app_shell = Path("frontend/src/layouts/AppShell.vue").read_text(encoding="utf-8")
        sidebar = Path("frontend/src/components/Sidebar.vue").read_text(encoding="utf-8")
        runtime_page = Path("frontend/src/pages/RuntimeCenter.vue").read_text(encoding="utf-8")
        loading_overlay = Path("frontend/src/components/runtime/RuntimeLoadingOverlay.vue").read_text(encoding="utf-8")

        self.assertIn("z-index: 0;", app_shell)
        self.assertIn("z-index: 100;", sidebar)
        self.assertIn("isolation: isolate;", runtime_page)
        self.assertIn("z-index: 40;", loading_overlay)

    def test_runtime_center_collapses_development_processes_by_default(self) -> None:
        runtime_center = Path("frontend/src/components/settings/RuntimeCenter.vue").read_text(encoding="utf-8")

        self.assertIn("showDevelopmentProcesses", runtime_center)
        self.assertIn("developmentProcesses", runtime_center)
        self.assertIn("visibleProcesses", runtime_center)
        self.assertIn(':data="visibleProcesses"', runtime_center)

    def test_runtime_center_treats_concurrent_collector_start_as_in_progress(self) -> None:
        runtime_center = Path("frontend/src/components/settings/RuntimeCenter.vue").read_text(encoding="utf-8")

        self.assertIn("result.already_starting === true", runtime_center)

    def test_runtime_process_client_exposes_explicit_full_scan(self) -> None:
        runtime_api = Path("frontend/src/api/runtimeCenter.ts").read_text(encoding="utf-8")

        self.assertIn("getRuntimeProcesses(full = false)", runtime_api)
        self.assertIn("?full=${String(full)}", runtime_api)

    def test_runtime_loading_is_owned_by_scroll_viewport(self) -> None:
        overlay_path = Path("frontend/src/components/runtime/RuntimeLoadingOverlay.vue")
        self.assertTrue(overlay_path.exists())

        page = Path("frontend/src/pages/RuntimeCenter.vue").read_text(encoding="utf-8")
        child = Path("frontend/src/components/settings/RuntimeCenter.vue").read_text(encoding="utf-8")
        overlay = overlay_path.read_text(encoding="utf-8")
        self.assertIn("RuntimeLoadingOverlay", page)
        self.assertIn('@loading="handleLoading"', page)
        self.assertIn('class="runtime-page-scroll"', page)
        self.assertIn("position: absolute;", overlay)
        self.assertNotIn('v-loading="loading"', child)

    def test_runtime_development_processes_are_loaded_on_demand(self) -> None:
        runtime_center = Path("frontend/src/components/settings/RuntimeCenter.vue").read_text(encoding="utf-8")

        self.assertIn("getRuntimeProcesses(true)", runtime_center)
        self.assertIn("toggleDevelopmentProcesses", runtime_center)
        self.assertGreaterEqual(runtime_center.count("refresh: false"), 2)

    def test_tauri_dev_server_avoids_npm_lifecycle_wrapper(self) -> None:
        config = json.loads(Path("src-tauri/tauri.conf.json").read_text(encoding="utf-8"))
        before_dev = config["build"]["beforeDevCommand"]

        self.assertIsInstance(before_dev, dict)
        self.assertFalse(before_dev["wait"])
        self.assertEqual(
            before_dev["script"],
            "node node_modules/vite/bin/vite.js frontend --host 127.0.0.1",
        )
        self.assertNotIn("npm", before_dev["script"].lower())

    def test_tauri_exit_cleans_managed_python_process_tree(self) -> None:
        main = Path("src-tauri/src/main.rs").read_text(encoding="utf-8")
        runtime = Path("src-tauri/src/runtime.rs").read_text(encoding="utf-8")
        sidecar = Path("src-tauri/src/sidecar.rs").read_text(encoding="utf-8")
        cargo = Path("src-tauri/Cargo.toml").read_text(encoding="utf-8")

        self.assertIn("tauri::RunEvent::Exit", main)
        self.assertIn("sidecar::stop_python_api", main)
        self.assertIn("job_handle", runtime)
        self.assertIn("JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE", sidecar)
        self.assertIn("AssignProcessToJobObject", sidecar)
        self.assertIn("close_job_handle", sidecar)
        self.assertIn("Win32_System_JobObjects", cargo)
        self.assertGreaterEqual(sidecar.count("process.child = Some(child);"), 2)
        self.assertIn("runtime.last_error = Some(error_message.clone());", sidecar)
        self.assertIn("if let Err(_error) = close_job_handle(job_handle)", sidecar)
        self.assertLess(runtime.index("process.job_handle.take()"), runtime.index("process.child.take()"))


if __name__ == "__main__":
    unittest.main()
