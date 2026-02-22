from pathlib import Path

import cv2
import logging

from hopilot.logging_config import get_logger


def sort_captured_images():
    logger = get_logger(__name__)
    # Placeholder: Load template matching model instead of YOLO
    # model = YOLO('models/playing-cards.pt')

    # Source directory
    source_dir = Path("recordings/screenshots/auto_capture")
    if not source_dir.exists():
        logger.error(f"Source directory {source_dir} does not exist.")
        return

    # Destination directories
    dataset_dir = Path("dataset")
    train_dir = dataset_dir / "train"

    # Get all png files
    image_files = list(source_dir.glob("*.png"))
    if not image_files:
        logger.error("No .png files found in auto_capture directory.")
        return

    # Process all files to train
    def process_files(files, dest_base):
        counters = {}
        for img_path in files:
            # Read image
            img = cv2.imread(str(img_path))
            if img is None:
                logger.error(f"Failed to read {img_path}")
                continue

            # Placeholder: Predict with template matching instead of YOLO
            # results = model.predict(source=img, imgsz=32, conf=0.1, save=False)
            # if not results or len(results[0].boxes) == 0:
            #     # Move to unmatched folder
            #     unmatched_dir = dest_base.parent / 'unmatched'
            #     unmatched_dir.mkdir(parents=True, exist_ok=True)
            #     shutil.move(str(img_path), str(unmatched_dir / img_path.name))
            #     print(f"Moved unmatched {img_path} to {unmatched_dir}")
            #     continue

            # # Get the class with highest confidence
            # boxes = results[0].boxes
            # best_idx = boxes.conf.argmax()
            # cls = int(boxes.cls[best_idx])
            # class_name = results[0].names[cls]

            # Placeholder: Assume class_name from template matching
            class_name = "placeholder_class"

            # Create directory if not exists
            class_dir = dest_base / class_name
            class_dir.mkdir(parents=True, exist_ok=True)

            # Get counter for this class
            if class_name not in counters:
                counters[class_name] = 1
            else:
                counters[class_name] += 1

            # Extract suffix from filename (e.g., _f1 from 1_f1.png)
            filename = img_path.name
            parts = filename.split("_")
            if len(parts) >= 2:
                suffix_part = parts[1].split(".")[0]
                suffix = f"_{suffix_part}"
            else:
                suffix = ""

            # Save as PNG with preserved suffix
            dest_path = class_dir / f"{counters[class_name]:04d}{suffix}.png"
            cv2.imwrite(str(dest_path), img)
            logger.info(f"Saved {img_path} to {dest_path}")

    process_files(image_files, train_dir)

    logger.info("Sorting complete.")


if __name__ == "__main__":
    sort_captured_images()
