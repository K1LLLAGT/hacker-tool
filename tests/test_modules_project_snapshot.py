# hacker-tool:generated
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


from modules.project import snapshot


class TestGenerated(unittest.TestCase):
    def test_importable(self) -> None:
        self.assertIsNotNone(snapshot)


if __name__ == "__main__":
    unittest.main()
