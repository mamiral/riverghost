import streamlit as st
from PIL import Image
import time
from card_detector import CardDetector
from poker_analyzer import PokerAnalyzer

st.title("HoPilot - Poker Hold'em Copilot")

# Initialize components
detector = CardDetector()
analyzer = PokerAnalyzer()

# Session state for assignments
if 'assignments' not in st.session_state:
    st.session_state.assignments = {}
if 'advice' not in st.session_state:
    st.session_state.advice = "No advice yet"
if 'image_path' not in st.session_state:
    st.session_state.image_path = None

# Input for image or video
option = st.selectbox("Select input type", ["Image", "Video"])

if option == "Image":
    uploaded_file = st.file_uploader("Choose an image", type=["png", "jpg", "jpeg"])
    if uploaded_file:
        # Save to temp
        with open("temp_image.jpg", "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.session_state.image_path = "temp_image.jpg"
        st.session_state.assignments = detector.detect_cards(st.session_state.image_path)
        phase = 'pre-flop'  # Simple
        hole_cards = []
        if st.session_state.assignments.get('hero_hole_1'):
            hole_cards.append(st.session_state.assignments['hero_hole_1'][0])
        if st.session_state.assignments.get('hero_hole_2'):
            hole_cards.append(st.session_state.assignments['hero_hole_2'][0])
        board_cards = []
        for slot in ['flop_1', 'flop_2', 'flop_3', 'turn', 'river']:
            if st.session_state.assignments.get(slot):
                board_cards.append(st.session_state.assignments[slot][0])
        st.session_state.advice = analyzer.get_advice(hole_cards, board_cards, phase)

elif option == "Video":
    video_file = st.file_uploader("Choose a video", type=["mp4", "avi"])
    if video_file:
        # For simplicity, process first frame
        import cv2
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            tmp.write(video_file.getbuffer())
            tmp_path = tmp.name
        cap = cv2.VideoCapture(tmp_path)
        ret, frame = cap.read()
        if ret:
            cv2.imwrite("temp_frame.jpg", frame)
            st.session_state.image_path = "temp_frame.jpg"
            st.session_state.assignments = detector.detect_cards(st.session_state.image_path)
            phase = 'pre-flop'
            hole_cards = []
            if st.session_state.assignments.get('hero_hole_1'):
                hole_cards.append(st.session_state.assignments['hero_hole_1'][0])
            if st.session_state.assignments.get('hero_hole_2'):
                hole_cards.append(st.session_state.assignments['hero_hole_2'][0])
            board_cards = []
            for slot in ['flop_1', 'flop_2', 'flop_3', 'turn', 'river']:
                if st.session_state.assignments.get(slot):
                    board_cards.append(st.session_state.assignments[slot][0])
            st.session_state.advice = analyzer.get_advice(hole_cards, board_cards, phase)
        cap.release()

# Display
col1, col2 = st.columns(2)

with col1:
    if st.session_state.image_path:
        try:
            image = Image.open(st.session_state.image_path)
            st.image(image, caption="Current Image", use_column_width=True)
        except:
            st.write("Image not available")

with col2:
    st.subheader("Hole Cards")
    hole1 = st.session_state.assignments.get('hero_hole_1')
    hole2 = st.session_state.assignments.get('hero_hole_2')
    if hole1:
        st.write(f"{hole1[0]} (conf: {hole1[1]:.2f})")
    else:
        st.write("Not detected")
    if hole2:
        st.write(f"{hole2[0]} (conf: {hole2[1]:.2f})")
    else:
        st.write("Not detected")

    st.subheader("Board Cards")
    board_slots = ['flop_1', 'flop_2', 'flop_3', 'turn', 'river']
    for slot in board_slots:
        card = st.session_state.assignments.get(slot)
        if card:
            st.write(f"{slot}: {card[0]} (conf: {card[1]:.2f})")
        else:
            st.write(f"{slot}: Not detected")

    st.subheader("Advice")
    st.write(st.session_state.advice)