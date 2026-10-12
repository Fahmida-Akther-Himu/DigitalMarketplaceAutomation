# Results saved by one test file and read by the next one, e.g.
# framework_agreement_amendment.py -> framework_agreement_requisition.py -> framework_agreement_order.py
# Files are saved in <project>/test_data/ (git-ignored, never pushed).
import json
from pathlib import Path

TEST_DATA_DIR = Path(__file__).resolve().parents[1] / "test_data"


def save_result(name, data):
    TEST_DATA_DIR.mkdir(exist_ok=True)
    result_file = TEST_DATA_DIR / f"{name}.json"
    result_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Result saved: {result_file}")
    return result_file


def load_result(name, created_by):
    # created_by: the test file that saves this result (shown when the result is missing)
    result_file = TEST_DATA_DIR / f"{name}.json"
    assert result_file.is_file(), f"{result_file.name} not found: run {created_by} first"
    return json.loads(result_file.read_text(encoding="utf-8"))
