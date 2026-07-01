from __future__ import annotations

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="Adaptive Market Decoder quant-engine CLI")
    parser.add_argument(
        "command",
        choices=["ingest", "features", "labels", "train", "validate", "backtest", "scanner", "export"],
    )
    args = parser.parse_args()
    print(f"{args.command}: use the FastAPI route or dashboard workflow for V1 local execution.")


if __name__ == "__main__":
    main()
