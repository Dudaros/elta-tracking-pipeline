from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from elta_tracker import parse_tracking_payload  # noqa: E402
from elta_tracker import build_summary_tables  # noqa: E402
import pandas as pd


def test_parse_tracking_payload_success() -> None:
    payload = {
        "status": 1,
        "result": {
            "NF123456789GR": {
                "result": [
                    {"status": "Picked up", "date": "2025-01-14", "time": "10:10", "place": "Athens"},
                    {"status": "Delivered", "date": "2025-01-15", "time": "15:30", "place": "Piraeus"},
                ]
            }
        },
    }
    events = parse_tracking_payload(payload, "NF123456789GR")

    assert len(events) == 2
    assert events[0]["Voucher"] == "NF123456789GR"
    assert events[1]["Status"] == "Delivered"


def test_parse_tracking_payload_missing_voucher_returns_empty() -> None:
    payload = {"status": 1, "result": {}}
    events = parse_tracking_payload(payload, "NF000000000GR")
    assert events == []


def test_parse_tracking_payload_status_zero_returns_empty() -> None:
    payload = {"status": 0}
    events = parse_tracking_payload(payload, "NF000000000GR")
    assert events == []


def test_build_summary_tables_returns_latest_and_counts() -> None:
    events_df = pd.DataFrame(
        [
            {"Voucher": "A", "Status": "In Transit", "Date": "14/01/2025", "Time": "10:00", "Location": "ATH"},
            {"Voucher": "A", "Status": "Delivered", "Date": "15/01/2025", "Time": "12:00", "Location": "ATH"},
            {"Voucher": "B", "Status": "In Transit", "Date": "15/01/2025", "Time": "11:30", "Location": "PIR"},
        ]
    )
    latest_df, counts_df = build_summary_tables(events_df)

    assert len(latest_df) == 2
    assert latest_df[latest_df["Voucher"] == "A"]["Status"].iloc[0] == "Delivered"
    delivered = counts_df[counts_df["Status"] == "Delivered"]["Vouchers"].iloc[0]
    assert delivered == 1
