import cv2
import numpy as np
import os
import argparse
import shutil
from pathlib import Path

def load_suite_templates(templates_dir):
    templates = {}
    red_suites = ['hearts', 'diamonds']
    black_suites = ['spades', 'clubs_orig']
    red_templates = {}
    black_templates = {}
    for file in os.listdir(templates_dir):
        if file.endswith(('.png', '.jpg', '.jpeg')):
            template_path = os.path.join(templates_dir, file)
            template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
            if template is None:
                print(f"Error: Failed to load template {template_path} as grayscale")
                continue
            name = os.path.splitext(file)[0]
            templates[name] = template
            if name in red_suites:
                red_templates[name] = template
            elif name in black_suites:
                # Map clubs_orig to clubs
                suite_name = 'clubs' if name == 'clubs_orig' else name
                black_templates[suite_name] = template
    return red_templates, black_templates

def load_rank_templates(templates_dir):
    normal_templates = {}
    edge_templates = {}
    contour_templates = {}
    for file in os.listdir(templates_dir):
        if file.endswith(('.png', '.jpg', '.jpeg')):
            template_path = os.path.join(templates_dir, file)
            template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
            if template is None:
                print(f"Error: Failed to load template {template_path} as grayscale")
                continue
            name = os.path.splitext(file)[0]
            # Store normal
            normal_templates[name] = template
            # Apply Canny edge detection
            edges = cv2.Canny(template, 100, 200)
            edge_templates[name] = edges
            # Find contours
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if contours:
                # Take the largest contour
                main_contour = max(contours, key=cv2.contourArea)
                contour_templates[name] = main_contour
    return normal_templates, edge_templates, contour_templates

def match_template(image, template, method=cv2.TM_CCOEFF_NORMED):
    res = cv2.matchTemplate(image, template, method)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
    return max_val, max_loc

def match_shapes(contour1, contour2):
    return cv2.matchShapes(contour1, contour2, cv2.CONTOURS_MATCH_I1, 0)

def get_top_matches(gray_image, templates, n=3):
    matches = []
    for name, template in templates.items():
        if template.shape[0] > gray_image.shape[0] or template.shape[1] > gray_image.shape[1]:
            continue  # Skip if template is larger than image
        score, loc = match_template(gray_image, template)
        matches.append((name, score))
    matches.sort(key=lambda x: x[1], reverse=True)
    return matches[:n]

def is_red_color(bgr_value):
    b, g, r = bgr_value
    # Red if R is highest and above threshold
    return r > 50 and r > g and r > b

def classify_suite(image):
    # Crop rank: y=0 to 18, full width
    rank_crop = image[0:18, :]
    
    # Crop suite: y=20 to bottom, full width
    suite_crop = image[20:, :]
    
    print(f"Image shape: {image.shape}, suite_crop shape: {suite_crop.shape}")
    
    # Get color of 5x5 area around center of suite_crop, vote on red
    h, w = suite_crop.shape[:2]
    center_y, center_x = h // 2, w // 2
    if h >= 5 and w >= 5:
        y1 = max(0, center_y - 2)
        y2 = min(h, center_y + 3)
        x1 = max(0, center_x - 2)
        x2 = min(w, center_x + 3)
        patch = suite_crop[y1:y2, x1:x2]
        red_votes = 0
        total_pixels = (y2 - y1) * (x2 - x1)
        for i in range(y2 - y1):
            for j in range(x2 - x1):
                pixel_bgr = patch[i, j]
                if is_red_color(pixel_bgr):
                    red_votes += 1
        color_is_red = red_votes > total_pixels // 2
        avg_bgr = np.mean(patch.reshape(-1, 3), axis=0)
        print(f"5x5 patch avg BGR: {avg_bgr}, {red_votes}/{total_pixels} red pixels, is_red: {color_is_red}")
    else:
        color_is_red = False  # Default to black if can't sample
        print(f"Cannot sample 5x5 patch, defaulting to black")
    
    # Convert suite to grayscale
    if len(suite_crop.shape) == 3:
        if suite_crop.shape[2] == 4:
            suite_crop = cv2.cvtColor(suite_crop, cv2.COLOR_BGRA2BGR)
        suite_gray = cv2.cvtColor(suite_crop, cv2.COLOR_BGR2GRAY)
    else:
        suite_gray = suite_crop
    
    return suite_gray, color_is_red, rank_crop

def main():
    parser = argparse.ArgumentParser(description='Match suite and rank templates with images in specified directory.')
    parser.add_argument('directory', help='Directory containing images to match')
    parser.add_argument('--debug-sorting', action='store_true', help='Copy images to validation directory organized by suite/rank')
    args = parser.parse_args()

    templates_dir = 'templates/suites'
    if not os.path.exists(templates_dir):
        print(f"Templates directory '{templates_dir}' does not exist.")
        return

    red_templates, black_templates = load_suite_templates(templates_dir)
    if not red_templates and not black_templates:
        print("No suite templates found.")
        return

    print(f"Loaded red templates: {list(red_templates.keys())}")
    print(f"Loaded black templates: {list(black_templates.keys())}")

    rank_templates_dir = 'templates/ranks'
    rank_normal = {}
    rank_edges = {}
    rank_contours = {}
    if os.path.exists(rank_templates_dir):
        rank_normal, rank_edges, rank_contours = load_rank_templates(rank_templates_dir)
        print(f"Loaded {len(rank_normal)} rank templates.")
    else:
        print(f"Rank templates directory '{rank_templates_dir}' does not exist.")

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
        suite_gray, is_red, rank_crop = classify_suite(image)
        
        # Match suite
        suite_top = get_top_matches(suite_gray, red_templates if is_red else black_templates)
        print(f"Top suite matches: {suite_top}")
        if suite_top and suite_top[0][1] >= 0.8:
            suite_match, suite_score = suite_top[0]
            suite_result = f"matched {suite_match} (score {suite_score:.2f})"
        else:
            if suite_top:
                suite_match, suite_score = suite_top[0]
                suite_result = f"best {suite_match} (score {suite_score:.2f})"
            else:
                suite_result = "no templates"
            if suite_top and suite_top[0][1] < 0.8:
                unmatched.append(img_path.name)
        
        # Convert rank_crop to gray
        if len(rank_crop.shape) == 3:
            if rank_crop.shape[2] == 4:
                rank_crop = cv2.cvtColor(rank_crop, cv2.COLOR_BGRA2BGR)
            rank_gray = cv2.cvtColor(rank_crop, cv2.COLOR_BGR2GRAY)
        else:
            rank_gray = rank_crop
        rank_top = get_top_matches(rank_gray, rank_normal)
        print(f"Top rank matches: {rank_top}")
        if rank_top and rank_top[0][1] >= 0.6:
            rank_match, rank_score = rank_top[0]
            rank_result = f"matched {rank_match} (score {rank_score:.2f})"
        else:
            # Try with Canny edges
            rank_edges_img = cv2.Canny(rank_gray, 100, 200)
            rank_top_edges = get_top_matches(rank_edges_img, rank_edges)
            print(f"Top rank edges matches: {rank_top_edges}")
            if rank_top_edges and rank_top_edges[0][1] >= 0.6:
                rank_match, rank_score = rank_top_edges[0]
                rank_result = f"matched {rank_match} (edges, score {rank_score:.2f})"
            else:
                # Try with contour matching
                contours, _ = cv2.findContours(rank_edges_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                if contours:
                    main_contour = max(contours, key=cv2.contourArea)
                    best_match = None
                    best_score = float('inf')
                    for name, template_contour in rank_contours.items():
                        score = cv2.matchShapes(main_contour, template_contour, cv2.CONTOURS_MATCH_I1, 0)
                        if score < best_score:
                            best_score = score
                            best_match = name
                    print(f"Best contour match: {best_match}, score {best_score:.4f}")
                    if best_score < 0.5:  # Some threshold for shape matching
                        rank_result = f"matched {best_match} (contour, score {best_score:.4f})"
                    else:
                        rank_result = f"best contour: {best_match} (score {best_score:.4f})"
                else:
                    rank_result = "no contours"
                if rank_top_edges and rank_top_edges[0][1] < 0.6:
                    unmatched_ranks.append(img_path.name)
        
        print(f"{img_path.name}: Suite {suite_result}, Rank {rank_result}")

        # Check if failed match
        is_failed = not suite_result.startswith("matched ") or not rank_result.startswith("matched ")
        if is_failed:
            failed_matches.append(img_path.name)

        if args.debug_sorting:
            # Determine suite name
            if suite_result.startswith("matched "):
                suite_name = suite_result.split()[1]
            elif suite_result.startswith("best "):
                suite_name = suite_result.split()[1]
            else:
                suite_name = "unknown_suite"
            
            # Determine rank name
            if rank_result.startswith("matched "):
                rank_name = rank_result.split()[1]
            elif rank_result.startswith("best contour: "):
                rank_name = rank_result.split()[2]
            elif rank_result.startswith("best "):
                rank_name = rank_result.split()[1]
            elif rank_result.startswith("top: "):
                # Take first rank
                parts = rank_result[5:].split(", ")
                if parts:
                    rank_name = parts[0].split()[0]
                else:
                    rank_name = "unknown_rank"
            else:
                rank_name = "unknown_rank"
            
            print(f"Classified {img_path.name} as {suite_name}/{rank_name}")
            if is_failed:
                dest_dir = "validation/failed"
            else:
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