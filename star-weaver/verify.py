"""Run the application checks and write an inspectable verification receipt."""
import json
import platform
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent


class Receipt(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.checks = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.checks.append({'check': test.id(), 'status': 'PASS'})

    def addFailure(self, test, error):
        super().addFailure(test, error)
        self.checks.append({'check': test.id(), 'status': 'FAIL', 'detail': str(error[1])})

    def addError(self, test, error):
        super().addError(test, error)
        self.checks.append({'check': test.id(), 'status': 'FAIL', 'detail': str(error[1])})


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.discover(str(ROOT / 'tests'), pattern='test_*.py')
    result = unittest.TextTestRunner(verbosity=2, resultclass=Receipt).run(suite)
    report = {'version': '0.2.0', 'executed_at_utc': datetime.now(timezone.utc).isoformat(),
              'scope': 'Actual skill engine, lineage engine, persistence and HTTP boundary checks using isolated synthetic state',
              'python': platform.python_version(), 'platform': platform.system(),
              'test_count': result.testsRun, 'status': 'PASS' if result.wasSuccessful() else 'FAIL',
              'checks': result.checks}
    (ROOT / 'verification' / 'unit-results.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    raise SystemExit(0 if result.wasSuccessful() else 1)
