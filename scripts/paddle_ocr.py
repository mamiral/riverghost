import os

# Force CPU mode and disable GPU optimizations
os.environ["FLAGS_enable_pir_api"] = "0"
os.environ["FLAGS_use_mkldnn"] = "0"
os.environ["CUDA_VISIBLE_DEVICES"] = ""  # Disable GPU
os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"  # Disable connectivity check to model hosters
os.environ["PADDLE_PDX_SKIP_CHECK"] = "True"  # Additional skip check variable
os.environ["FLAGS_enable_paddle_cloud"] = "0"  # Disable paddle cloud features

from paddleocr import PaddleOCR
from PIL import Image
import numpy as np
import matplotlib.pyplot as plt
import cv2

# Initialize PaddleOCR with English language
ocr = PaddleOCR(lang='en')

# List of specific image files to process
image_files = [
    'recordings/screenshots/2.png'
]

# List of regions to process with their coordinates
regions = [
    {
        'name': 'hero_stack',
        'coords': (20, 755, 125, 775),  # Wider crop to capture full text
        'expected': '49 BB'
    },
    {
        'name': 'villain_1_name', 
        'coords': (12, 581, 84, 595),
        'expected': 'Grayed out (folded)'
    },
    {
        'name': 'villain_1_stack',
        'coords': (25, 597, 69, 611),
        'expected': 'No text (folded)'
    },
    {
        'name': 'villain_2_name',
        'coords': (16, 326, 86, 341),
        'expected': 'Bigfish!888'
    },
    {
        'name': 'total_pot',
        'coords': (172, 368, 235, 397),
        'expected': 'Total Pot 3.5 BB'
    },
    {
        'name': 'hero_bet',
        'coords': (129, 652, 159, 665),
        'expected': '1 BB'
    }
]

# Process each image
for img_path in image_files:
    print(f"\nProcessing: {img_path}")
    print("=" * 50)

    try:
        # Open the image once
        img = Image.open(img_path)

        # Process each region
        for region in regions:
            print(f"\n--- Processing {region['name']} ---")
            coords = region['coords']

            # Crop the image for this region
            cropped = img.crop(coords)
            cropped_np = np.array(cropped)

            # Special preprocessing for regions with text on colored backgrounds
            if region['name'] == 'total_pot':
                # Yellow text on green background
                hsv = cv2.cvtColor(cropped_np, cv2.COLOR_RGB2HSV)
                
                # Extract yellow channel (yellow has high S and V values)
                # Yellow is around H: 20-40, S: 100-255, V: 100-255
                lower_yellow = np.array([20, 100, 100])
                upper_yellow = np.array([40, 255, 255])
                yellow_mask = cv2.inRange(hsv, lower_yellow, upper_yellow)
                
                # Also try to enhance overall contrast
                gray = cv2.cvtColor(cropped_np, cv2.COLOR_RGB2GRAY)
                clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
                enhanced = clahe.apply(gray)
                
                # Combine approaches: use enhanced contrast where yellow mask is weak
                combined = cv2.bitwise_or(enhanced, yellow_mask)
                
                # Apply threshold to create binary image
                _, thresh = cv2.threshold(combined, 127, 255, cv2.THRESH_BINARY)
                
                # Convert back to RGB format for PaddleOCR (it expects RGB images)
                cropped_np = cv2.cvtColor(thresh, cv2.COLOR_GRAY2RGB)
            elif region['name'] == 'hero_bet':
                # Save original for display
                original_cropped = cropped_np.copy()
                
                # Quick OCR preprocessing for white text on green background
                img_scaled = cv2.resize(cropped_np, None, fx=2.8, fy=2.8, interpolation=cv2.INTER_CUBIC)
                
                b, g, r = cv2.split(img_scaled)
                enhanced = b
                
                _, thresh = cv2.threshold(enhanced, 165, 255, cv2.THRESH_BINARY)
                
                kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2,2))
                clean = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=2)
                clean = cv2.morphologyEx(clean, cv2.MORPH_OPEN, kernel, iterations=1)
                
                if np.mean(clean) > 100:
                    clean = cv2.bitwise_not(clean)
                
                # Convert back to RGB for PaddleOCR
                cropped_np = cv2.cvtColor(clean, cv2.COLOR_GRAY2RGB)
            else:
                # Standard preprocessing for other regions
                pass

            # Display the cropped image before OCR
            if region['name'] == 'hero_bet':
                # Display preprocessing steps as subplots
                fig, axes = plt.subplots(1, 4, figsize=(16, 3))
                
                # Original cropped image
                axes[0].imshow(original_cropped)
                axes[0].set_title("Original")
                axes[0].axis('off')
                
                # Scaled up image
                axes[1].imshow(img_scaled)
                axes[1].set_title("Scaled 2.8x")
                axes[1].axis('off')
                
                # Blue channel thresholded
                axes[2].imshow(thresh, cmap='gray')
                axes[2].set_title("Blue Channel Thresholded")
                axes[2].axis('off')
                
                # Final processed
                axes[3].imshow(clean, cmap='gray')
                axes[3].set_title("Final Processed")
                axes[3].axis('off')
                
                plt.tight_layout()
                plt.show()
            else:
                plt.figure(figsize=(8, 3))
                plt.imshow(cropped_np, cmap='gray' if len(cropped_np.shape) == 2 else None)
                plt.title(f"Cropped {region['name']}: {img_path}\nExpected: {region.get('expected', 'Unknown')}")
                plt.axis('off')
                plt.show()

            # Run OCR on cropped image
            result = ocr.ocr(cropped_np)

            # Print detailed results
            if result and isinstance(result, list) and len(result) > 0:
                detection_data = result[0]
                if 'rec_texts' in detection_data:
                    texts = detection_data['rec_texts']
                    scores = detection_data['rec_scores']
                    boxes = detection_data.get('rec_boxes', [])
                    
                    print(f"Found {len(texts)} text detection(s):")
                    for i, (text, score) in enumerate(zip(texts, scores), 1):
                        print(f"\nDetection {i}:")
                        print(f"  Text: '{text}'")
                        print(f"  Confidence: {score:.4f}")
                        if i <= len(boxes):
                            bbox = boxes[i-1]
                            # Calculate bounding box dimensions for rectangle [x1,y1,x2,y2,x3,y3,x4,y4]
                            x_coords = bbox[::2]  # Even indices are x coordinates
                            y_coords = bbox[1::2]  # Odd indices are y coordinates
                            width = max(x_coords) - min(x_coords)
                            height = max(y_coords) - min(y_coords)
                            print(f"  Bounding Box: {bbox}")
                            print(f"  Dimensions: {width:.1f} x {height:.1f} pixels")
                else:
                    print(f"Unexpected result format: {type(result)} - {result}")
            else:
                print("No text detected.")

    except Exception as e:
        print(f"Error processing {img_path}: {str(e)}")

print("\nOCR analysis completed.")