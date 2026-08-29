"""Command-line entry point.

Examples:
    python -m orchestrator --text "Apple is buying a Beijing startup for $1B."
    python -m orchestrator --file input.txt --out report.md
    python -m orchestrator --text "..." --roles ner sentiment
    NLP_USE_MOCK=1 python -m orchestrator --text "..."   # offline, no API key
"""

import argparse
from pathlib import Path

from . import analyze_sync


def main() -> None:
    p = argparse.ArgumentParser(
        prog="orchestrator",
        description="Parallel NLP subagent orchestrator (LangGraph + DeepSeek).",
    )
    p.add_argument("--text", help="Input text to analyze")
    p.add_argument("--file", help="Path to a UTF-8 text file to analyze")
    p.add_argument("--out", help="Write the Markdown report to this path")
    p.add_argument(
        "--roles",
        nargs="*",
        help="Subset of roles to run (default: all). "
        "Available: classification, ner, summarization, sentiment, translation",
    )
    args = p.parse_args()

    text = args.text
    if text is None and args.file:
        text = Path(args.file).read_text(encoding="utf-8")
    if not text:
        p.error("provide --text or --file")

    result = analyze_sync(text, roles=args.roles)
    report = result["final_report"]
    print(report)
    if args.out:
        Path(args.out).write_text(report, encoding="utf-8")
        print(f"\n[written] {args.out}")


if __name__ == "__main__":
    main()
