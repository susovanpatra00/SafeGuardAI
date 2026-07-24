"""
scripts/test_video_pipeline.py

Runs the full video pipeline on a test video and prints a summary.

Usage:
    python scripts/test_video_pipeline.py --video data/uploads/test_video.mp4
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from pipeline.process_video import process_video  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True, help="Path to input video")
    parser.add_argument("--output", default="data/uploads/annotated_output.mp4")
    parser.add_argument("--source", default="Test Upload")
    parser.add_argument("--sample-every", type=int, default=5,
                         help="Run detection every N frames (higher = faster, less accurate)")
    parser.add_argument("--threshold", type=float, default=0.40)
    args = parser.parse_args()

    print(f"Processing {args.video}...")
    print(f"(sampling every {args.sample_every} frames, threshold={args.threshold})\n")

    result = process_video(
        video_path=args.video,
        output_path=args.output,
        source_label=args.source,
        sample_every_n_frames=args.sample_every,
        confidence_threshold=args.threshold,
    )

    print("Done.\n")
    print(f"  Output video:        {result.output_path}")
    print(f"  Frames analyzed:     {result.total_frames_processed}")
    print(f"  Total detections:    {result.total_detections}")
    print(f"    Known:             {result.known_count}")
    print(f"    Unknown:           {result.unknown_count}")
    print(f"  Time taken:          {result.duration_seconds}s")
    print(f"\nRecognition events have been logged to the recognition_logs table.")
    print(f"Query them with: SELECT * FROM recognition_logs ORDER BY id DESC LIMIT 20;")


if __name__ == "__main__":
    main()