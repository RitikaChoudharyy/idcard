import os
import dlib
import cv2
import numpy as np
from PIL import Image, ImageChops
from rembg import remove
import streamlit as st

# Initialize dlib's face detector
detector = dlib.get_frontal_face_detector()

# Define padding sizes in pixels
padding_size_top = 415  # Approximately 5 cm at passport photo resolution
padding_size_sides = 186  # Approximately 1 cm at passport photo resolution

# Define input and output folders
input_folder = r"C:\Users\Shree\Desktop\downloadfolder"
output_folder = input_folder  # Overwrite the same folder after processing

# Streamlit app
st.title("ID Card Image Processor and Generator")

# Upload CSV file with user information
uploaded_csv = st.file_uploader("Upload CSV file with user information", type=["csv"])

# Upload image files
uploaded_files = st.file_uploader("Choose images", accept_multiple_files=True, type=["png", "jpg", "jpeg", "bmp", "gif"])

# Process images and generate ID cards
if st.button("Process Images and Generate ID Cards"):
    if uploaded_files and uploaded_csv:
        # Process each uploaded image
        for uploaded_file in uploaded_files:
            # Save uploaded image to input folder
            image_path = os.path.join(input_folder, uploaded_file.name)
            with open(image_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            # Read image
            image = cv2.imread(image_path)
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            # Detect faces using dlib
            faces = detector(gray)

            for i, face in enumerate(faces):
                # Get the coordinates of the face
                x, y, w, h = (face.left(), face.top(), face.width(), face.height())

                # Calculate new bounding box with padding
                x1 = max(x - padding_size_sides, 0)
                y1 = max(y - padding_size_top, 0)
                x2 = min(x + w + padding_size_sides, image.shape[1])
                y2 = min(y + h + padding_size_sides, image.shape[0])

                # Extract the face region with padding
                face_with_padding = image[y1:y2, x1:x2]

                # Convert the face region to PIL Image for background removal
                face_with_padding_pil = Image.fromarray(cv2.cvtColor(face_with_padding, cv2.COLOR_BGR2RGB))

                # Remove background using rembg
                face_no_bg = remove(face_with_padding_pil)

                # Composite the original image and the image with removed background
                face_with_bg = ImageChops.composite(face_with_padding_pil, face_no_bg, face_no_bg)

                # Create a white background image
                white_background = Image.new("RGB", (144, 149), (255, 255, 255))

                # Resize the face image to passport size (144x149 pixels)
                resized_face = face_with_bg.resize((144, 149), Image.LANCZOS)

                # Paste the face image onto the white background
                white_background.paste(resized_face, (0, 0), resized_face)

                # Save the passport size image, overwriting the original image
                white_background.save(image_path)

        st.success("Image processing complete. Images have been updated in the folder.")

        # Now call your existing ID card generator function
        generate_id_cards_from_csv(uploaded_csv, input_folder)

        st.success("ID cards generated successfully.")
    else:
        st.error("Please upload both images and a CSV file.")

def generate_id_cards_from_csv(csv_file, image_folder):
    import pandas as pd

    # Read the CSV file
    df = pd.read_csv(csv_file)

    # Iterate over each row in the CSV and generate ID cards using the updated images
    for index, row in df.iterrows():
        # Extract information from the CSV
        name = row['Name']
        position = row['Position']
        image_name = row['Image']

        # Path to the updated image
        image_path = os.path.join(image_folder, image_name)

        # Generate the ID card using your existing logic
        # (Implement your ID card generation code here, using the updated image_path)

        # Example:
        # create_id_card(name, position, image_path)
        pass

    st.info("ID card generation logic should be implemented here.")
