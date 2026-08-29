"""Tests for the data-acquisition helpers (network-free parts only)."""
import zipfile

from criterialogic.data import download as dl
from criterialogic.data.loaders.chia import load_chia_dir


def test_n2c2_status_absent(tmp_path):
    st = dl.n2c2_status(tmp_path / "n2c2_2018")
    assert st["present"] is False
    assert st["n_files"] == 0
    assert "n2c2.dbmi.hms.harvard.edu" in st["portal"]
def test_extract_and_parse_chia_brat(tmp_path):
    # Simulate the figshare archive layout (nested subfolder) and the loader's recursive read.
    zpath = tmp_path / "Chia_w_scope.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        zf.writestr("Chia_w_scope/NCT00000001.ann",
                    "T1\tCondition 0 14\ttype 2 diabetes\nT2\tDrug 19 26\taspirin\n")
        zf.writestr("Chia_w_scope/NCT00000001.txt", "type 2 diabetes and aspirin\n")
    dest = tmp_path / "chia"
    assert dl._extract_archives([zpath], dest) == 1
    forms = load_chia_dir(str(dest))
    assert len(forms) == 2
    assert all(f.source.value == "chia" for f in forms)
def test_chia_idempotent_skip(tmp_path):
    dest = tmp_path / "chia"
    dest.mkdir()
    (dest / "x.ann").write_text("T1\tCondition 0 4\ttest\n")
    assert dl.download_chia_figshare(dest=dest)["status"] == "already_present"
def test_verify_summary(tmp_path):
    summary = dl.verify(tmp_path)
    assert summary["chia_ann_files"] == 0
    assert summary["ctgov_cached_queries"] == 0
    assert summary["n2c2"]["present"] is False
