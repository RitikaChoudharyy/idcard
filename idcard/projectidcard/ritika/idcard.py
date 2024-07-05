import os
import cv2
import numpy as np
from PIL import Image, ImageChops
from rembg import remove
import streamlit as st
import pandas as pd

# Initialize OpenCV's Haar cascade face detector
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# Define padding sizes in pixels
padding_size_top = 415  # Approximately 5 cm at passport photo resolution
padding_size_sides = 186  # Approximately 1 cm at passport photo resolution

# Define input and output folders
input_folder = r"C:\Users\Shree\Desktop\downloadfolder"
output_folder = input_folder  # Overwrite the same folder after processing

def preprocess_images(input_folder):
    for filename in os.listdir(input_folder):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
            image_path = os.path.join(input_folder, filename)
            image = cv2.imread(image_path)
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
            
            for (x, y, w, h) in faces:
                x1 = max(x - padding_size_sides, 0)
                y1 = max(y - padding_size_top, 0)
                x2 = min(x + w + padding_size_sides, image.shape[1])
                y2 = min(y + h + padding_size_sides, image.shape[0])

                face_with_padding = image[y1:y2, x1:x2]
                face_with_padding_pil = Image.fromarray(cv2.cvtColor(face_with_padding, cv2.COLOR_BGR2RGB))
                face_no_bg = remove(face_with_padding_pil)
                face_with_bg = ImageChops.composite(face_with_padding_pil, face_no_bg, face_no_bg)
                white_background = Image.new("RGB", (144, 149), (255, 255, 255))
                resized_face = face_with_bg.resize((144, 149), Image.LANCZOS)
                white_background.paste(resized_face, (0, 0), resized_face)
                white_background.save(image_path)

# Streamlit app
st.title("ID Card Image Processor and Generator")

# Upload CSV file with user information
uploaded_csv = st.file_uploader("Upload CSV file with user information", type=["csv"])

# Upload image files
uploaded_files = st.file_uploader("Choose images", accept_multiple_files=True, type=["png", "jpg", "jpeg", "bmp", "gif"])

# Process images and generate ID cards
if st.button("Process Images and Generate ID Cards"):
    if uploaded_files and uploaded_csv:
        # Save uploaded images to input folder
        for uploaded_file in uploaded_files:
            image_path = os.path.join(input_folder, uploaded_file.name)
            with open(image_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

        # Preprocess images
        preprocess_images(input_folder)
        st.success("Image processing complete. Images have been updated in the folder.")

        # Read the CSV file
        csv_data = pd.read_csv(uploaded_csv)

        # Example of generating ID cards (this is where you would implement your ID card generation logic)
        # For demonstration purposes, we'll just show the processed images
        st.subheader("Processed Images")
        for filename in os.listdir(input_folder):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
                image_path = os.path.join(input_folder, filename)
                st.image(image_path, caption=f"Processed image: {filename}")

    else:
        st.error("Please upload both images and a CSV file.")

# Add your ID card generation logic here if necessary

if __name__ == '__main__':
    st.title("ID Card Generation App")
    main()
