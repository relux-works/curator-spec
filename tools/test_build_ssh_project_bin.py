"""Controls prove the draft validator rejects each changed vector's defect."""
import copy
import json
import unittest
import build_ssh_project_bin as checks

class BuildSSHProjectBinControls(unittest.TestCase):
    # Complete unmodified vectors pass; an inherited PATH plant must fail for
    # executable selection, independently of any credential or fixture error.
    def test_ssh_selection_plant(self):
        v = json.loads((checks.ROOT / "ssh-policy.json").read_text())
        checks.validate_ssh(v)
        bad = copy.deepcopy(v)
        bad["inherited_path"] = True
        with self.assertRaisesRegex(ValueError, "SSH selection must ignore inherited PATH"):
            checks.validate_ssh(bad)

    # A mismatched sidecar cannot be adopted or mutate state. The nearby
    # valid adoption/removal controls keep reject-everything from passing.
    def test_legacy_ownership_plant(self):
        v = json.loads((checks.ROOT / "project-bin.json").read_text())
        checks.validate_ownership(v)
        bad = copy.deepcopy(v)
        bad["cases"][2]["code"] = None
        with self.assertRaisesRegex(ValueError, "legacy enforcement evidence refusal required"):
            checks.validate_ownership(bad)

    # Every added code row has a targeted wrong-code plant; unchanged vectors
    # pass first, and a rejection must identify the intended mapping defect.
    def test_diagnostic_code_plants(self):
        ssh = json.loads((checks.ROOT / "ssh-policy.json").read_text())
        checks.validate_ssh(ssh)
        bad = copy.deepcopy(ssh)
        next(c for c in bad["cases"] if c["condition"] == "no-ssh")["code"] = None
        with self.assertRaisesRegex(ValueError, "credential refusal and snapshot mapping"):
            checks.validate_ssh(bad)
        v = json.loads((checks.ROOT / "project-bin.json").read_text())
        checks.validate_ownership(v)
        for index, row in enumerate(v["diagnostic_cases"]):
            with self.subTest(condition=row["condition"]):
                bad = copy.deepcopy(v)
                bad["diagnostic_cases"][index]["code"] = "wrong_code"
                with self.assertRaisesRegex(ValueError, "project diagnostic refusal and preservation mapping"):
                    checks.validate_ownership(bad)
