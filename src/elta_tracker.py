import argparse
import json
import logging
from pathlib import Path
from time import sleep
from datetime import datetime

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

TRACK_URL = "https://www.elta-courier.gr/track.php"
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
    "Origin": "https://www.elta-courier.gr",
    "Referer": "https://www.elta-courier.gr/",
}


def setup_logger(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(message)s",
    )


def build_session(retries: int, backoff_factor: float) -> requests.Session:
    session = requests.Session()
    retry_strategy = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "POST", "OPTIONS"],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update(DEFAULT_HEADERS)
    return session


def parse_tracking_payload(payload: dict, voucher: str) -> list[dict]:
    if payload.get("status") != 1:
        return []

    result = payload.get("result", {}).get(voucher, {}).get("result", [])
    if not isinstance(result, list):
        return []

    events = []
    for event in result:
        events.append(
            {
                "Voucher": voucher,
                "Status": event.get("status", "N/A"),
                "Date": event.get("date", "N/A"),
                "Time": event.get("time", "N/A"),
                "Location": event.get("place", "N/A"),
            }
        )
    return events


def fetch_tracking_events(session: requests.Session, voucher: str, timeout: int) -> list[dict]:
    data = {"number": voucher, "s": "0"}
    response = session.post(TRACK_URL, data=data, timeout=timeout)
    response.raise_for_status()

    payload_text = response.content.decode("utf-8-sig")
    payload = json.loads(payload_text)
    return parse_tracking_payload(payload, voucher)


def load_vouchers(input_file: Path | None, input_column: str, vouchers_inline: str | None) -> list[str]:
    vouchers: list[str] = []

    if vouchers_inline:
        vouchers.extend([v.strip() for v in vouchers_inline.split(",") if v.strip()])

    if input_file:
        if not input_file.exists():
            raise FileNotFoundError(f"Input file not found: {input_file}")

        suffix = input_file.suffix.lower()
        if suffix in {".xlsx", ".xls"}:
            df = pd.read_excel(input_file)
            if input_column not in df.columns:
                raise ValueError(f"Column '{input_column}' not found in {input_file}")
            vouchers.extend([str(v).strip() for v in df[input_column].dropna().tolist() if str(v).strip()])
        elif suffix == ".csv":
            df = pd.read_csv(input_file)
            if input_column not in df.columns:
                raise ValueError(f"Column '{input_column}' not found in {input_file}")
            vouchers.extend([str(v).strip() for v in df[input_column].dropna().tolist() if str(v).strip()])
        elif suffix == ".txt":
            lines = input_file.read_text(encoding="utf-8").splitlines()
            vouchers.extend([line.strip() for line in lines if line.strip()])
        else:
            raise ValueError("Unsupported input file. Use .xlsx, .csv, or .txt")

    deduped = list(dict.fromkeys(vouchers))
    return deduped


def build_summary_tables(events_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if events_df.empty:
        latest = pd.DataFrame(columns=["Voucher", "Status", "Date", "Time", "Location"])
        counts = pd.DataFrame(columns=["Status", "Vouchers"])
        return latest, counts

    working = events_df.copy()
    working["_event_ts"] = pd.to_datetime(
        working["Date"].astype(str) + " " + working["Time"].astype(str),
        errors="coerce",
        dayfirst=True,
    )
    latest = (
        working.sort_values(by=["Voucher", "_event_ts"], ascending=[True, True])
        .groupby("Voucher", as_index=False)
        .tail(1)[["Voucher", "Status", "Date", "Time", "Location"]]
        .sort_values(by="Voucher")
        .reset_index(drop=True)
    )
    counts = (
        latest["Status"]
        .fillna("N/A")
        .value_counts()
        .rename_axis("Status")
        .reset_index(name="Vouchers")
    )
    return latest, counts


def write_markdown_summary(
    summary_markdown: Path,
    total_vouchers: int,
    total_events: int,
    failed: list[str],
    latest_df: pd.DataFrame,
    counts_df: pd.DataFrame,
) -> None:
    summary_markdown.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# ELTA Tracking Daily Summary",
        "",
        f"- Generated at: {datetime.now().isoformat(timespec='seconds')}",
        f"- Vouchers processed: {total_vouchers}",
        f"- Tracking events captured: {total_events}",
        f"- Failed vouchers: {len(failed)}",
    ]
    if failed:
        lines.append(f"- Failed list: {', '.join(failed)}")

    lines.extend(["", "## Latest Status Counts", ""])
    if counts_df.empty:
        lines.append("No status counts available.")
    else:
        lines.extend(
            [
                "| Status | Vouchers |",
                "|---|---:|",
                *[f"| {row.Status} | {row.Vouchers} |" for row in counts_df.itertuples(index=False)],
            ]
        )

    lines.extend(["", "## Latest Status Per Voucher", ""])
    if latest_df.empty:
        lines.append("No events available.")
    else:
        lines.extend(
            [
                "| Voucher | Status | Date | Time | Location |",
                "|---|---|---|---|---|",
                *[
                    f"| {row.Voucher} | {row.Status} | {row.Date} | {row.Time} | {row.Location} |"
                    for row in latest_df.itertuples(index=False)
                ],
            ]
        )

    summary_markdown.write_text("\n".join(lines) + "\n", encoding="utf-8")
    logging.info("Saved markdown summary to %s", summary_markdown)


def save_output(
    records: list[dict],
    output_file: Path,
    summary_markdown: Path | None,
    total_vouchers: int,
    failed: list[str],
) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    events_df = pd.DataFrame(records, columns=["Voucher", "Status", "Date", "Time", "Location"])
    latest_df, counts_df = build_summary_tables(events_df)

    if output_file.suffix.lower() == ".csv":
        events_df.to_csv(output_file, index=False)
        latest_csv = output_file.with_name(f"{output_file.stem}_latest_status.csv")
        counts_csv = output_file.with_name(f"{output_file.stem}_status_counts.csv")
        latest_df.to_csv(latest_csv, index=False)
        counts_df.to_csv(counts_csv, index=False)
        logging.info("Saved latest status to %s", latest_csv)
        logging.info("Saved status counts to %s", counts_csv)
    else:
        with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
            events_df.to_excel(writer, sheet_name="events", index=False)
            latest_df.to_excel(writer, sheet_name="latest_status", index=False)
            counts_df.to_excel(writer, sheet_name="status_counts", index=False)
    logging.info("Saved %s rows to %s", len(events_df), output_file)

    if summary_markdown:
        write_markdown_summary(
            summary_markdown=summary_markdown,
            total_vouchers=total_vouchers,
            total_events=len(events_df),
            failed=failed,
            latest_df=latest_df,
            counts_df=counts_df,
        )


def run(
    vouchers: list[str],
    output_file: Path,
    timeout: int,
    retries: int,
    backoff_factor: float,
    delay_seconds: float,
    summary_markdown: Path | None,
) -> int:
    if not vouchers:
        logging.warning("No vouchers found to process.")
        return 0

    session = build_session(retries=retries, backoff_factor=backoff_factor)
    all_events: list[dict] = []
    failed: list[str] = []

    total = len(vouchers)
    for idx, voucher in enumerate(vouchers, start=1):
        try:
            logging.info("Processing %s/%s: %s", idx, total, voucher)
            events = fetch_tracking_events(session, voucher, timeout=timeout)
            all_events.extend(events)
        except Exception as exc:  # noqa: BLE001
            logging.error("Failed voucher %s: %s", voucher, exc)
            failed.append(voucher)
        finally:
            if delay_seconds > 0:
                sleep(delay_seconds)

    save_output(
        records=all_events,
        output_file=output_file,
        summary_markdown=summary_markdown,
        total_vouchers=total,
        failed=failed,
    )
    if failed:
        logging.warning("Failed vouchers: %s", ", ".join(failed))
    logging.info("Done. Vouchers: %s | Events: %s | Failed: %s", total, len(all_events), len(failed))
    return 0 if not failed else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Track ELTA Courier vouchers and export status events.")
    parser.add_argument("--input-file", type=Path, default=None, help="Input file (.xlsx/.csv/.txt).")
    parser.add_argument("--input-column", type=str, default="Voucher", help="Column name for voucher IDs.")
    parser.add_argument("--vouchers", type=str, default=None, help="Comma-separated voucher numbers.")
    parser.add_argument("--output-file", type=Path, default=Path("output/tracking_results.xlsx"), help="Output file (.xlsx or .csv).")
    parser.add_argument("--timeout", type=int, default=20, help="Request timeout in seconds.")
    parser.add_argument("--retries", type=int, default=3, help="Retry attempts for transient failures.")
    parser.add_argument("--backoff-factor", type=float, default=0.8, help="Backoff factor for retries.")
    parser.add_argument("--delay-seconds", type=float, default=0.5, help="Delay between requests.")
    parser.add_argument(
        "--summary-markdown",
        type=str,
        default="output/tracking_summary.md",
        help="Markdown summary path. Use 'none' to disable.",
    )
    parser.add_argument("--log-level", type=str, default="INFO", help="Logging level.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    setup_logger(args.log_level)
    vouchers = load_vouchers(args.input_file, args.input_column, args.vouchers)
    summary_arg = (args.summary_markdown or "").strip()
    summary_md = None if summary_arg.lower() in {"", "none", "null"} else Path(summary_arg)
    exit_code = run(
        vouchers=vouchers,
        output_file=args.output_file,
        timeout=args.timeout,
        retries=args.retries,
        backoff_factor=args.backoff_factor,
        delay_seconds=args.delay_seconds,
        summary_markdown=summary_md,
    )
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
