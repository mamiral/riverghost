import os
import cv2
import requests
from ultralytics import YOLO
from card_layout import CardLayout

class CardDetector:
    def __init__(self, model_path='models/playing-cards.pt', model_url='https://huggingface.co/koolguy06/playing-cards/resolve/main/playing-cards.pt'):
        self.model_path = model_path
        self.model_url = model_url
        self.model = None
        self.layout = CardLayout()
        self._load_model()

    def _load_model(self):
        if not os.path.exists(self.model_path):
            print(f"Downloading model to {self.model_path}...")
            response = requests.get(self.model_url)
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            with open(self.model_path, 'wb') as f:
                f.write(response.content)
            print("Model downloaded.")

        self.model = YOLO(self.model_path)

    def detect_cards(self, image_path, conf=0.1, imgsz=1280):
        """
        Detect cards in an image.
        Returns dict of slot -> (name, conf) or None
        """
        results = self.model.predict(source=image_path, save=False, conf=conf, imgsz=imgsz)

        if not results:
            return {}

        boxes = results[0].boxes
        if len(boxes) == 0:
            return {}

        # Sort by x-coordinate (left to right)
        sorted_indices = boxes.xyxy[:, 0].argsort()
        detected_cards = []
        for idx in sorted_indices:
            cls = int(boxes.cls[idx])
            conf_val = boxes.conf[idx].item()
            name = results[0].names[cls]
            xyxy = boxes.xyxy[idx]
            detected_cards.append((name, conf_val, xyxy))

        # Assign to slots
        assignments = self.layout.assign_cards(detected_cards)
        return assignments

    def process_video_frame(self, frame, conf=0.1, imgsz=1280):
        """
        Detect cards in a video frame (numpy array).
        """
        # Save frame temporarily or process directly
        # For now, assume frame is image path, but can extend
        return self.detect_cards(frame, conf, imgsz)