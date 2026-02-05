import cv2
import numpy as np
import os
import argparse
import shutil
from pathlib import Path

def load_rank_templates(templates_dir):
    """Load rank templates and normalize to 0-1 range like test_template_matching.py"""
    templates = {}
    for file in os.listdir(templates_dir):
        if file.endswith(('.png', '.jpg', '.jpeg')):
            template_path = os.path.join(templates_dir, file)
            template = cv2.imread(template_path)
            if template is None:
                print(f"Error: Failed to load template {template_path}")
                continue

            # Convert to grayscale if needed
            if len(template.shape) == 3:
                template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
            else:
                template_gray = template

            # Normalize to 0-1 range (assuming it's already binary 0-255)
            template_norm = template_gray.astype(np.float32) / 255.0

            name = os.path.splitext(file)[0]
            templates[name] = template_norm
            print(f"Loaded rank template: {name} {template.shape} -> {template_norm.shape}")

    return templates

def convert_to_white_hot(image, threshold=200):
    """Convert image to 1-bit white hot (white pixels become 1, others 0)"""
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Create binary mask where white pixels (> threshold) are 255, others are 0
    _, binary = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)

    # Convert to 1-bit (0 or 1)
    binary_1bit = (binary / 255).astype(np.uint8)

    return binary_1bit

def match_template_correlation(image_normalized, template, method=cv2.TM_CCOEFF_NORMED):
    """Perform template matching using correlation like test_template_matching.py"""
    # Ensure image is large enough for template
    if image_normalized.shape[0] < template.shape[0] or image_normalized.shape[1] < template.shape[1]:
        return None

    # Perform template matching
    result = cv2.matchTemplate(image_normalized, template, method)

    # Get best match
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

    # Calculate confidence - shift to 0-1 range
    confidence = (max_val + 1.0) / 2.0

    return max_val, confidence

def get_top_matches_correlation(normalized_image, templates, n=3):
    """Get top matches using correlation-based template matching"""
    matches = []
    for name, template in templates.items():
        result = match_template_correlation(normalized_image, template)
        if result is not None:
            score, confidence = result
            matches.append((name, score, confidence))
    matches.sort(key=lambda x: x[1], reverse=True)
    return matches[:n]

def detect_card_color(bgr_value):
    """Detect the specific color of a card based on BGR values"""
    b, g, r = int(bgr_value[0]), int(bgr_value[1]), int(bgr_value[2])

    # White/bright pixels first (text/symbols) - exclude from color voting
    # Very strict white threshold since card backgrounds are bright but tinted
    if r > 245 and g > 245 and b > 245:
        return "white"

    # Blue (diamonds) - for average background color, blue should dominate
    if b > 100 and b > r + 20 and b > g + 20:
        return "blue"
    
    # Red (hearts) - for average background color, red should dominate
    if r > 100 and r > b + 20 and r > g + 20:
        return "red"
    
    # Green (clubs) - for average background color, green should dominate
    if g > 100 and g > r + 20 and g > b + 20:
        return "green"
    
    # Black (spades) - for average background color, all channels should be low
    if r < 80 and g < 80 and b < 80:
        return "black"

    # Everything else is unknown
    return "unknown"

def classify_suite(image):
    """Classify suite based on background color analysis, return suite name"""
    # Crop suite area: y=20 to bottom, full width
    suite_crop = image[20:, :]

    print(f"Image shape: {image.shape}, suite_crop shape: {suite_crop.shape}")

    # Average all non-white pixels in the suite area for robust color detection
    h, w = suite_crop.shape[:2]
    
    # Collect all non-white pixels for averaging
    background_pixels = []
    
    for i in range(h):
        for j in range(w):
            pixel_bgr = suite_crop[i, j]
            b, g, r = int(pixel_bgr[0]), int(pixel_bgr[1]), int(pixel_bgr[2])
            
            # Exclude very bright/white pixels (symbols)
            #if not (r > 240 and g > 240 and b > 240):
            if not (r > 128 and g > 128 and b > 128):
                background_pixels.append(pixel_bgr)
    
    if len(background_pixels) > 0:
        # Calculate average BGR of background pixels
        avg_bgr = np.mean(background_pixels, axis=0)
        
        # Classify based on the average background color
        b_avg, g_avg, r_avg = avg_bgr
        color = detect_card_color(avg_bgr)
        
        print(f"Background pixels: {len(background_pixels)}, avg BGR: {avg_bgr}, detected color: {color}")
        
        # Map color to suite
        if color == "blue":
            suite_name = "diamonds"
        elif color == "red":
            suite_name = "hearts"
        elif color == "green":
            suite_name = "clubs"
        elif color == "black":
            suite_name = "spades"
        else:
            suite_name = "unknown"
    else:
        suite_name = "unknown"
        print(f"No background pixels found, defaulting to unknown")

    # Crop rank area for processing
    rank_crop = image[0:18, :]

    return suite_name, rank_crop

def main():
    parser = argparse.ArgumentParser(description='Match card images using color-based suite detection and 1-bit template matching for ranks.')
    parser.add_argument('directory', help='Directory containing images to match')
    parser.add_argument('--debug-sorting', action='store_true', help='Copy images to validation directory organized by suite/rank')
    args = parser.parse_args()

    # Load rank templates using the new correlation-based approach
    rank_templates_dir = 'templates'
    rank_templates = {}
    if os.path.exists(rank_templates_dir):
        rank_templates = load_rank_templates(rank_templates_dir)
        print(f"Loaded {len(rank_templates)} rank templates.")
    else:
        print(f"Rank templates directory '{rank_templates_dir}' does not exist.")
        return

    if not rank_templates:
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
        image = cv2.imread(str(img_path))
        if image is None:
            print(f"{img_path.name}: Failed to read")
            continue

        print(f"Processing {img_path.name}:")
        suite_name, rank_crop = classify_suite(image)
        
        # Suite is now determined by color analysis
        suite_result = f"detected {suite_name} (color-based)"
        
        # Convert rank_crop to 1-bit white hot for correlation matching
        rank_1bit = convert_to_white_hot(rank_crop)
        
        # Match rank using correlation-based template matching
        rank_top = get_top_matches_correlation(rank_1bit.astype(np.float32), rank_templates)
        print(f"Top rank matches: {rank_top}")
        if rank_top and rank_top[0][1] >= 0.6:  # Using correlation score threshold
            rank_match, rank_score, confidence = rank_top[0]
            rank_result = f"matched {rank_match} (score {rank_score:.2f}, conf {confidence:.2f})"
        else:
            if rank_top:
                rank_match, rank_score, confidence = rank_top[0]
                rank_result = f"best {rank_match} (score {rank_score:.2f}, conf {confidence:.2f})"
            else:
                rank_result = "no matches"
            unmatched_ranks.append(img_path.name)
        
        print(f"{img_path.name}: Suite {suite_result}, Rank {rank_result}")

        # Check if failed match (suite is always detected, but rank might fail)
        is_failed = not rank_result.startswith("matched ")
        if is_failed:
            failed_matches.append(img_path.name)

        if args.debug_sorting:
            # For debug sorting, we use the detected color-based suite
            # Note: This will be "red" or "black", not specific suites
            suite_sort_name = suite_name
            
            # Determine rank name
            if rank_result.startswith("matched "):
                rank_name = rank_result.split()[1]
            elif rank_result.startswith("best "):
                rank_name = rank_result.split()[1]
            else:
                rank_name = "unknown_rank"
            
            print(f"Classified {img_path.name} as {suite_sort_name}/{rank_name}")
            if is_failed:
                dest_dir = "validation/failed"
            else:
                dest_dir = f"validation/{suite_sort_name}/{rank_name}"
                dest_dir = f"validation/{suite_name}/{rank_name}"
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