"""Windows-default encoding witnesses for leaf-1 tooling, without Windows."""
import os
from pathlib import Path
import subprocess
import sys
import unittest


# Claim: the publication validator, generator check and source-control loader
# read UTF-8 files correctly when implicit text I/O instead uses cp1252. The
# child first proves that this fallback fails on a real UTF-8 byte sequence;
# this is a decoding regression, not a simulated schema verdict.
DRIVER = r'''
import builtins
import io
import locale
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

original = io.open

def windows_open(file, mode='r', buffering=-1, encoding=None, errors=None,
                 newline=None, closefd=True, opener=None):
    if 'b' not in mode and encoding in (None, 'locale'):
        encoding = locale.getpreferredencoding(False)
    return original(file, mode, buffering, encoding, errors, newline, closefd, opener)

with patch.object(locale, 'getpreferredencoding', return_value='cp1252'), \
     patch.object(io, 'open', windows_open), \
     patch.object(builtins, 'open', windows_open):
    with tempfile.TemporaryDirectory() as temp:
        witness = Path(temp) / 'unicode.txt'
        witness.write_bytes(b'\xc4\x8d')
        try:
            witness.read_text()
        except UnicodeDecodeError:
            pass
        else:
            raise AssertionError('cp1252 default control did not fail')
        assert witness.read_text(encoding='utf-8') == '\u010d'
    sys.path.insert(0, str(Path('tools').resolve()))
    if sys.argv[1] == 'publication':
        import validate
        validate.validate_project_context_leaf1()
    elif sys.argv[1] == 'generator':
        import generate_project_context_vectors as generator
        sys.argv = [generator.__file__, '--check']
        generator.main()
    elif sys.argv[1] == 'control':
        import check_project_context_leaf1_controls as controls
        controls.run_case(next(c for c in controls.MANIFEST['cases']
                               if c['name'] == 'snapshot-manifest-negative-zero'))
    else:
        raise AssertionError('unknown entry')
print('cp1252 default: UTF-8 entry passed')
'''


class ProjectContextEncodingTests(unittest.TestCase):
    def test_non_utf8_default(self):
        env = dict(os.environ, PYTHONUTF8='0', PYTHONIOENCODING='cp1252',
                   PYTHONDONTWRITEBYTECODE='1')
        for entry in ('publication', 'generator', 'control'):
            with self.subTest(entry=entry):
                result = subprocess.run(
                    [sys.executable, '-B', '-c', DRIVER, entry],
                    cwd=Path(__file__).resolve().parents[1], env=env,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    encoding='utf-8', errors='replace', check=False,
                )
                self.assertEqual(result.returncode, 0, entry + ': ' + result.stderr)
                self.assertIn('cp1252 default: UTF-8 entry passed', result.stdout)
