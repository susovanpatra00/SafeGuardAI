import argparse

from src.pipeline.run import main


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SafeGuardAI — Number Plate Detection & OCR")
    parser.add_argument(
        "--config", default="configs/config.yaml", help="Path to config YAML"
    )
    args = parser.parse_args()
    main(config_path=args.config)
