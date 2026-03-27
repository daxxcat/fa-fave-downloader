import unittest
from fa_fave_downloader.cli import main


class TestCli(unittest.TestCase):
    def test_main_runs_without_error(self):
        # This is a placeholder test. Replace with actual tests.
        # For now, just ensure main() doesn't raise an exception.
        try:
            main()
        except SystemExit:
            pass  # main() might call sys.exit, which is fine for CLI


if __name__ == "__main__":
    unittest.main()
