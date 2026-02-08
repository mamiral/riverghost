from paddleocr import PaddleOCR
import os

os.environ["FLAGS_enable_pir_api"] = "0"
os.environ["FLAGS_use_mkldnn"] = "0"

# Initialize PaddleOCR with English language
ocr = PaddleOCR(lang='en')

# List of specific image files to process
image_files = [
    'recordings/screenshots/J3.png',
    'recordings/screenshots/10.png'
]

# Process each image
for img_path in image_files:
    print(f"\nProcessing: {img_path}")
    print("=" * 50)

    try:
        # Run OCR
        result = ocr.predict(img_path)

        # Print detailed results
        if result and 'rec_texts' in result[0] and result[0]['rec_texts']:
            detections = list(zip(result[0]['rec_polys'], result[0]['rec_texts'], result[0]['rec_scores']))
            print(f"Found {len(detections)} text detection(s):")
            for i, (bbox, text, confidence) in enumerate(detections, 1):
                print(f"\nDetection {i}:")
                print(f"  Text: '{text}'")
                print(f"  Confidence: {confidence:.4f}")
                print(f"  Bounding Box: {bbox}")
                # Calculate bounding box dimensions
                x_coords = [point[0] for point in bbox]
                y_coords = [point[1] for point in bbox]
                width = max(x_coords) - min(x_coords)
                height = max(y_coords) - min(y_coords)
                print(f"  Dimensions: {width:.1f} x {height:.1f} pixels")
        else:
            print("No text detected.")

    except Exception as e:
        print(f"Error processing {img_path}: {str(e)}")

print("\nOCR analysis completed.")