import cv2
import numpy as np
import os
import argparse
import shutil
from pathlib import Path
from card_matcher import CardMatcher

def main():
    parser = argparse.ArgumentParser(description='Match card images using color-based suite detection and 1-bit template matching for ranks.')
    parser.add_argument('directory', help='Directory containing images to match')
    parser.add_argument('--debug-sorting', action='store_true', help='Copy images to validation directory organized by suite/rank')
    args = parser.parse_args()

    # Initialize card matcher
    card_matcher = CardMatcher()
    if not card_matcher.rank_templates:
        print("No rank templates found.")
        return

    image_dir = Path(args.directory)
    if not image_dir.exists():
        print(f"Image directory '{args.directory}' does not exist.")
        return

    image_files = list(image_dir.glob('*.png')) + list(image_dir.glob('*.jpg')) + list(image_dir.glob('*.jpeg'))
    if not image_files:
        print("No image files found in the specified directory.")
        return

    failed_matches = []
    unmatched = []
    unmatched_ranks = []
    for img_path in image_files:
        print(f"Processing {img_path.name}:")

        # Use CardMatcher to recognize the card
        result = card_matcher.recognize_card(img_path)

        if result['error']:
            print(f"{img_path.name}: {result['error']}")
            continue

        suite_name = result['suite']
        rank_name = result['rank']
        rank_score = result['rank_score']
        rank_confidence = result['rank_confidence']

        # Format results for display
        suite_result = f"detected {suite_name} (color-based)"

        if rank_name and rank_score >= 0.6:
            rank_result = f"matched {rank_name} (score {rank_score:.2f}, conf {rank_confidence:.2f})"
        elif rank_name:
            rank_result = f"best {rank_name} (score {rank_score:.2f}, conf {rank_confidence:.2f})"
            unmatched_ranks.append(img_path.name)
        else:
            rank_result = "no matches"
            unmatched_ranks.append(img_path.name)

        print(f"{img_path.name}: Suite {suite_result}, Rank {rank_result}")

        # Check if failed match
        is_failed = not result['success']
        if is_failed:
            failed_matches.append(img_path.name)

        if args.debug_sorting:
            # Determine destination directory
            if is_failed:
                dest_dir = "validation/failed"
            else:
                dest_dir = f"validation/{suite_name}/{rank_name or 'unknown_rank'}"

            os.makedirs(dest_dir, exist_ok=True)
            shutil.copy(str(img_path), dest_dir)
            print(f"Copied {img_path.name} to {dest_dir}")

    # Output failed matches report
    if failed_matches:
        print(f"\nFailed matches ({len(failed_matches)}): {', '.join(failed_matches)}")
    else:
        print("\nAll matches successful.")

    if unmatched or unmatched_ranks:
        summary = []
        if unmatched:
            summary.append(f"{len(unmatched)} suites not matched: {', '.join(unmatched)}")
        if unmatched_ranks:
            summary.append(f"{len(unmatched_ranks)} ranks not matched: {', '.join(unmatched_ranks)}")
        print(f"\nSummary: {'; '.join(summary)}")
    else:
        print("\nSummary: All cards matched successfully.")

if __name__ == "__main__":
    main()