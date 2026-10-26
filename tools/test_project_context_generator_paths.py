"""Generator path portability against unchanged committed corpus bytes."""
import contextlib
import io
from pathlib import Path, PurePosixPath, PureWindowsPath
import shutil
import tempfile
import unittest
from unittest.mock import patch

import generate_project_context_vectors as generator


class ProjectContextGeneratorPathTests(unittest.TestCase):
    def run_generator(self, corpus, flavour, check):
        relative_to = type(corpus).relative_to

        def native_relative(path, *args, **kwargs):
            relative = relative_to(path, *args, **kwargs)
            if args == (corpus,):
                return flavour(*relative.parts)
            return relative

        argv = ['generate_project_context_vectors.py'] + (['--check'] if check else [])
        with patch.object(generator, 'CORPUS', corpus), patch.object(
                type(corpus), 'relative_to', native_relative), patch('sys.argv', argv):
            with contextlib.redirect_stdout(io.StringIO()) as output:
                generator.main()
        return output.getvalue()

    def snapshot(self, corpus):
        return {p.relative_to(corpus).as_posix(): p.read_bytes()
                for p in corpus.rglob('*') if p.is_file()}

    # Both native relative-path spellings match the canonical slash-separated
    # corpus keys in check and write modes; regeneration leaves all bytes intact.
    def test_native_paths_preserve_corpus(self):
        for flavour in (PurePosixPath, PureWindowsPath):
            for check in (True, False):
                with self.subTest(flavour=flavour.__name__, check=check):
                    with tempfile.TemporaryDirectory() as directory:
                        corpus = Path(directory) / 'corpus'
                        shutil.copytree(generator.CORPUS, corpus)
                        before = self.snapshot(corpus)
                        output = self.run_generator(corpus, flavour, check)
                        self.assertIn('427 leaf-1 grammar cases:', output)
                        self.assertEqual(self.snapshot(corpus), before)

    # A genuine extra nested JSON file is refused under either native spelling,
    # before any corpus bytes change, in both check and write modes.
    def test_obsolete_native_paths_refuse_without_writes(self):
        for flavour in (PurePosixPath, PureWindowsPath):
            for check in (True, False):
                with self.subTest(flavour=flavour.__name__, check=check):
                    with tempfile.TemporaryDirectory() as directory:
                        corpus = Path(directory) / 'corpus'
                        shutil.copytree(generator.CORPUS, corpus)
                        (corpus / 'bytes' / 'obsolete.json').write_bytes(b'{"obsolete":true}\n')
                        before = self.snapshot(corpus)
                        with self.assertRaisesRegex(ValueError,
                                r'^obsolete corpus files: bytes/obsolete\.json$'):
                            self.run_generator(corpus, flavour, check)
                        self.assertEqual(self.snapshot(corpus), before)


if __name__ == '__main__':
    unittest.main()
