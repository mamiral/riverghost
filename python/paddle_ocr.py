from paddleocr import PaddleOCR
from PIL import Image, ImageDraw
import cv2  # For optional image loading if needed

# Initialize PaddleOCR with PP-OCRv3 settings
# - lang='en' for English-focused model (uses en_PP-OCRv3_det for detection)
# - ocr_version='PP-OCRv3': Force v3 models (if not default in your version)
ocr = PaddleOCR(lang='en',
                ocr_version='PP-OCRv3')  # Specify v3 explicitly

# Path to your image
img_path = 'recordings/screenshots/1.jpeg'  # Replace with your image file

# Run OCR
result = ocr.ocr(img_path)

# Print OCR results
print("Detected text regions:")
res = result[0]
for i in range(len(res['rec_texts'])):
    text = res['rec_texts'][i]
    score = res['rec_scores'][i]
    box = res['dt_polys'][i]
    print(f"Box: {box.tolist()}, Text: {text}, Confidence: {score}")

# Optional: Visualize the bounding boxes
image = Image.open(img_path).convert('RGB')
draw = ImageDraw.Draw(image)

res = result[0]
for i in range(len(res['rec_texts'])):
    box = res['dt_polys'][i]
    # Convert to integers and draw polygon
    points = [(int(p[0]), int(p[1])) for p in box]
    draw.polygon(points, outline='red', width=3)

image.save('detected_boxes_v3.jpg')
print("Image with detected boxes saved as 'detected_boxes_v3.jpg'")