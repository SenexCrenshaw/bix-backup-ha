from __future__ import annotations

from pathlib import Path
import unittest


class ReleaseWorkflowTests(unittest.TestCase):
    def test_release_zip_contains_integration_files_at_archive_root(self) -> None:
        workflow = (
            Path(__file__).resolve().parent.parent
            / ".github"
            / "workflows"
            / "release.yml"
        ).read_text(encoding="utf-8")

        self.assertIn("mkdir -p dist/payload", workflow)
        self.assertIn("cp -R custom_components/bix_backup/. dist/payload/", workflow)
        self.assertIn("cd dist/payload", workflow)
        self.assertIn("zip -r ../../bix_backup.zip .", workflow)
        self.assertNotIn("zip -r ../bix_backup.zip custom_components", workflow)


if __name__ == "__main__":
    unittest.main()
