import os
import dlib
import cv2
import numpy as np
from PIL import Image, ImageChops
from rembg import remove
import streamlit as st
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import textwrap
from fpdf import FPDF
import base64
from st_aggrid import AgGrid
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch, mm
import logging

logging.basicConfig(filename='app.log', level=logging.ERROR, format='%(asctime)s - %(message)s')

# Function to preprocess image (convert to RGB)
def preprocess_image(image_path):
    try:
        input_image = Image.open(image_path)
        final_image = input_image.convert("RGB")
        return final_image
    except Exception as e:
        st.error(f"Error opening image at image_path: {str(e)}")
        return None

def generate_card(data, template_path, image_folder, qr_folder):
    pic_id = str(data.get('ID', ''))
    if not pic_id:
        st.warning(f"Skipping record with missing ID: {data}")
        return None
    
    pic_path = os.path.join(image_folder, f"{pic_id}.jpg")
    st.write(f"Looking for image at path: {pic_path}")
    
    if not os.path.exists(pic_path):
        st.error(f"Image not found for ID: {pic_id} at path: {pic_path}")
        return None
    
    qr_path = os.path.join(qr_folder, f"{pic_id}.png")
    st.write(f"Looking for QR code at path: {qr_path}")
    
    if not os.path.exists(qr_path):
        st.error(f"QR code not found for ID: {pic_id} at path: {qr_path}")
        return None

    # Preprocess the image
    preprocessed_pic = preprocess_image(pic_path)
    if preprocessed_pic is None:
        return None
    
    try:
        preprocessed_pic = preprocessed_pic.resize((144, 145))
    except Exception as e:
        st.error(f"Error resizing image for ID: {pic_id}. Error: {str(e)}")
        return None

    try:
        template = Image.open(template_path)
        qr = Image.open(qr_path).resize((161, 159))
        
        template.paste(preprocessed_pic, (27, 113, 171, 258))
        template.paste(qr, (497, 109, 658, 268))
        
        draw = ImageDraw.Draw(template)
        
        try:
            font_path = "C:\\WINDOWS\\FONTS\\ARIAL.TTF"  # Update with your font path
            name_font = ImageFont.truetype(font_path, size=18)
        except IOError:
            name_font = ImageFont.load_default()
        
        # Adjust text wrapping and positioning
        wrapped_div = textwrap.fill(str(data['Division/Section']), width=22).title()
        draw.text((311, 121), wrapped_div, font=name_font, fill='black')
        
        division_input = data['Division/Section']
        head_name = get_head_by_division(division_input)
        wrapped_supri = textwrap.fill(str(head_name), width=20).title()
        draw.text((311, 170), wrapped_supri, font=name_font, fill='black')
        
        university = data.get('University', 'Not Available')
        draw.text((200, 356), university, font=name_font, fill='black')
        
        draw.text((305, 219), data['Internship Start Date'], font=name_font, fill='black')
        draw.text((303, 266), data['Internship End Date'], font=name_font, fill='black')
        draw.text((300, 312), str(data['Mobile']), font=name_font, fill='black')
        draw.text((621, 283), str(data['ID']), font=name_font, fill='black')
        
        wrapped_name = center_align_text_wrapper(data['Name'], width=22)
        name_bbox = name_font.getbbox(wrapped_name)
        name_width = name_bbox[2] - name_bbox[0]
        center_x = ((198 - name_width) / 2)
        draw.text((center_x, 260), wrapped_name, font=name_font, fill='black')
        
        return template
    
    except Exception as e:
        st.error(f"Error generating card for ID: {pic_id}. Error: {str(e)}")
        return None

# Function to center-align text with wrapping
def center_align_text_wrapper(text, width=15):
    words = text.split()
    lines = []
    current_line = ""

    for word in words:
        if len(current_line) + len(word) + 1 <= width:
            current_line += word + " "
        else:
            lines.append(current_line[:-1])
            current_line = word + " "

    lines.append(current_line[:-1])
    centered_lines = [line.center(width) for line in lines]
    centered_text = "\n".join(centered_lines)

    return centered_text

# Function to get the head by division
def get_head_by_division(division_name):
    divisions = {
        "Advanced Information Technologies Group": "Dr. Sanjay Singh",
        "Societal Electronics Group": "Dr. Udit Narayan Pal",
        "Industrial Automation": "Dr. S.S. Sadistap",
        "Vacuum Electronic Devices Group": "Dr. Sanjay Kr. Ghosh",
        "High-Frequency Devices & System Group": "Dr. Ayan Bandhopadhyay",
        "Semiconductor Sensors & Microsystems Group": "Dr. Suchandan Pal",
        "Semiconductor Process Technology Group": "Dr. Kuldip Singh",
        "Industrial R & D": "Mr. Ashok Chauhan",
        "High Power Microwave Systems Group": "Dr. Anirban Bera",
    }

    division_name = division_name.strip().title()
    return divisions.get(division_name, "Division not found or head information not available.")

def create_pdf(images, pdf_path):
    try:
        c = canvas.Canvas(pdf_path, pagesize=letter)

        # Define the dimensions and spacing for the grid
        grid_width = 2
        grid_height = 4
        image_width = 3.575 * inch
        image_height = 2.325 * inch
        spacing_x = 1.5 * mm
        spacing_y = 1.5 * mm

        # Calculate total width and height of the grid
        total_width = grid_width * (image_width + spacing_x)
        total_height = grid_height * (image_height + spacing_y)

        # Track the current page
        current_page = 0

        for i, image in enumerate(images):
            col = i % grid_width
            row = i // grid_width

            # Check if the current page is filled and there are more images to be processed
            if i > 0 and i % (grid_width * grid_height) == 0:
                # Start a new page
                current_page += 1
                c.showPage()

            # Calculate the starting position for each new page
            start_x = (letter[0] - total_width) / 2
            start_y = (letter[1] - total_height) / 2 - current_page * total_height

            # Calculate the position for the current image on the current page
            x = start_x + col * (image_width + spacing_x)
            y = start_y + row * (image_height + spacing_y)

            # Draw the image on the canvas
            c.drawInlineImage(image, x, y, width=image_width, height=image_height)

        # Save the PDF to the specified path
        c.save()

        return pdf_path  # Return the path where the PDF is saved

    except Exception as e:
        logging.error(f"Error creating PDF: {str(e)}")
        return None

def display_pdf(pdf_path):
    try:
        with open(pdf_path, "rb") as f:
            base64_pdf = base64.b64encode(f.read()).decode('utf-8')
            pdf_display = f'<a href="data:application/pdf;base64,{base64_pdf}" download="generated_id_cards.pdf">Download PDF</a>'
            st.markdown(pdf_display, unsafe_allow_html=True)
    except FileNotFoundError:
        st.error(f"PDF file '{pdf_path}' not found.")
    except Exception as e:
        st.error(f"Error displaying PDF: {str(e)}")

def preprocess_images(input_folder):
    temp_folder = os.path.join(input_folder, "temp")

    # Create temporary folder for processing
    if not os.path.exists(temp_folder):
        os.makedirs(temp_folder)

    # Initialize dlib's face detector
    detector = dlib.get_frontal_face_detector()

    # Define padding sizes in pixels
    padding_size_top = 472  # Approximately 10 cm at passport photo resolution
    padding_size_sides = 189  # Approximately 2 cm at passport photo resolution

    # Iterate through all images in the folder
    for filename in os.listdir(input_folder):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
            image_path = os.path.join(input_folder, filename)

            # Load image using dlib
            img = dlib.load_rgb_image(image_path)

            # Detect faces in the image
            faces = detector(img, 1)

            if len(faces) == 0:
                continue

            # Assuming there's only one face per image
            face = faces[0]

            # Extract face coordinates
            x, y, w, h = face.left(), face.top(), face.width(), face.height()

            # Add padding to the image
            top_padding = max(0, padding_size_top - y)
            bottom_padding = max(0, padding_size_top - (img.shape[0] - (y + h)))
            side_padding = max(0, padding_size_sides - x, padding_size_sides - (img.shape[1] - (x + w)))

            # Add padding to the image
            img_padded = cv2.copyMakeBorder(img, top_padding, bottom_padding, side_padding, side_padding,
                                            cv2.BORDER_CONSTANT, value=[255, 255, 255])

            # Convert to PIL image for further processing
            img_pil = Image.fromarray(img_padded)

            # Remove background
            img_no_bg = remove(img_pil)

            # Set a white background
            img_no_bg_with_white_bg = Image.new("RGBA", img_no_bg.size, (255, 255, 255))
            img_no_bg_with_white_bg.paste(img_no_bg, (0, 0), img_no_bg)

            # Resize image to passport size (3.5 x 4.5 cm at 300 dpi)
            img_resized = img_no_bg_with_white_bg.resize((413, 531))

            # Save the processed image to the temporary folder
            img_resized_path = os.path.join(temp_folder, filename)
            img_resized.save(img_resized_path)

    return temp_folder

def main():
    st.title("ID Card Generator")

    # File uploader for CSV
    uploaded_file = st.file_uploader("Upload CSV file", type=["csv"])
    template_path = st.text_input("Enter the template image path (JPEG/PNG):")
    image_folder = st.text_input("Enter the folder path containing images:")
    qr_folder = st.text_input("Enter the folder path containing QR codes:")
    process_images = st.checkbox("Preprocess Images")

    if process_images and image_folder:
        try:
            temp_folder = preprocess_images(image_folder)
            st.success(f"Images have been preprocessed and saved to {temp_folder}.")
            image_folder = temp_folder  # Update image folder to temporary folder
        except Exception as e:
            st.error(f"Error preprocessing images: {str(e)}")

    if uploaded_file and template_path and image_folder and qr_folder:
        df = pd.read_csv(uploaded_file)
        df = df.dropna(subset=['ID'])

        selected_data = st.multiselect("Select Data", df.columns.tolist(), default=df.columns.tolist())
        if selected_data:
            selected_df = df[selected_data]

            # Display DataFrame with st_aggrid
            AgGrid(selected_df)

            if st.button("Generate ID Cards"):
                images = []
                for _, row in selected_df.iterrows():
                    data = row.to_dict()
                    card = generate_card(data, template_path, image_folder, qr_folder)
                    if card:
                        images.append(card)

                if images:
                    pdf_path = "generated_id_cards.pdf"
                    pdf_path = create_pdf(images, pdf_path)

                    if pdf_path:
                        display_pdf(pdf_path)
                    else:
                        st.error("Failed to create PDF.")
                else:
                    st.error("No images to generate ID cards.")

if __name__ == "__main__":
    main()
