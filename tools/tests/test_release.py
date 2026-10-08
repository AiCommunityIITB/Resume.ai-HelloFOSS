import importlib.util
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('check_release', Path(__file__).resolve().parents[1] / 'check_release.py')
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class ReleaseChecks(unittest.TestCase):
    def check(self, name, content):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding='utf-8')
            return checker.inspect(d)[1]

    def test_provider_key(self):
        self.assertTrue(self.check('bad.txt', 'AIza' + 'A' * 35))
        self.assertTrue(self.check('bad.txt', 'csk-' + 'A' * 30))
        self.assertTrue(self.check('bad.txt', 'gsk_' + 'A' * 30))

    def test_database_credential(self):
        self.assertTrue(self.check('config.txt', 'postgresql' + '://user:synthetic-password@localhost/db'))

    def test_private_asset(self):
        self.assertTrue(self.check('resume.pdf', 'synthetic'))
        self.assertTrue(self.check('.env', 'KEY='))

    def test_blank_template(self):
        self.assertFalse(self.check('.env.example', 'API_KEY=\nPOSTGRES_PASSWORD=\nDATABASE_URL=\n'))
        self.assertFalse(self.check('.env.example', 'API_KEY=""\nPOSTGRES_PASSWORD=""\nDATABASE_URL=""\n'))
        self.assertTrue(self.check('.env.example', 'API_KEY=synthetic\n'))

    def test_identifier_column(self):
        self.assertTrue(self.check('fixture.csv', 'filename,score\nsynthetic,1\n'))

    def test_numeric_fixture(self):
        self.assertFalse(self.check('backend/ai_models/whitespace_layout_scorer/fixture.csv', 'score,ratio\n1,0.5\n'))

    def test_environment_reference(self):
        self.assertFalse(self.check('compose.yml', 'POSTGRES_PASSWORD: "${POSTGRES_PASSWORD:?Set locally}"\n'))

    def test_syntax_check(self):
        self.assertTrue(self.check('invalid.py', 'def broken('))
        self.assertFalse(self.check('valid.py', 'x = 1\n'))


if __name__ == '__main__':
    unittest.main()
