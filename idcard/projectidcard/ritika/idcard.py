import os
import dlib
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageChops
from rembg import remove
import streamlit as st
import pandas as pd
from st_aggrid import AgGrid
from fpdf import FPDF
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch, mm
import base64
import logging

logging.basicConfig(filename='app.log', level=logging.ERROR, format='%(asctime)s - %(message)s')

# Initialize dlib's face detector
detector = dlib.get_frontal_face_detector()

# Function to preprocess image (detect face, remove background, resize)
def preprocess_image(image_path):
    try:
        input_image = Image.open(image_path).convert("RGB")
        open_cv_image = np.array(input_image)

        gray = cv2.cvtColor(open_cv_image, cv2.COLOR_BGR2GRAY)
        faces = detector(gray)
        if len(faces) == 0:
            st.error(f"No faces detected in the image at {image_path}.")
            return None

        face = faces[0]
        x, y, w, h = (face.left(), face.top(), face.width(), face.height())
        face_image = open_cv_image[y:y + h, x:x + w]

        face_image_pil = Image.fromarray(cv2.cvtColor(face_image, cv2.COLOR_BGR2RGB))
        face_no_bg = remove(face_image_pil)

        resized_face = face_no_bg.resize((144, 149), Image.LANCZOS)
        white_background = Image.new("RGB", (144, 149), (255, 255, 255))
        white_background.paste(resized_face, (0, 0), resized_face)

        return white_background
    except Exception as e:
        st.error(f"Error processing image at {image_path}: {str(e)}")
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
        template = Image.open(template_path).convert("RGB")
        qr = Image.open(qr_path).convert("RGB").resize((161, 159))

        # Ensure the dimensions for pasting are correct
        preprocessed_pic = preprocessed_pic.resize((144, 149)).convert("RGB")
        template.paste(preprocessed_pic, (27, 113))
        template.paste(qr, (497, 109))
        
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
        st.error("Error: PDF file not found.")
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")

def main():
    st.title('ID Card Generator')

    # Adding a sidebar for navigation
    st.sidebar.title("Navigation")
    options = ["Single ID Card", "Multiple ID Cards (comma-separated IDs)", "Generate ID Cards from CSV"]
    choice = st.sidebar.selectbox("Choose an option", options)

    template_path = "template.jpg"
    image_folder = "images"
    qr_folder = "qr"

    if choice == "Single ID Card":
        st.header("Generate a Single ID Card")
        ID = st.text_input("Enter ID")
        if st.button("Generate ID Card"):
            if ID:
                data = {
                    'ID': ID,
                    'Division/Section': st.text_input("Division/Section"),
                    'Name': st.text_input("Name"),
                    'University': st.text_input("University"),
                    'Internship Start Date': st.text_input("Internship Start Date"),
                    'Internship End Date': st.text_input("Internship End Date"),
                    'Mobile': st.text_input("Mobile")
                }
                card = generate_card(data, template_path, image_folder, qr_folder)
                if card:
                    st.image(card)
            else:
                st.error("Please enter an ID")

    elif choice == "Multiple ID Cards (comma-separated IDs)":
        st.header("Generate Multiple ID Cards")
        IDs = st.text_input("Enter comma-separated IDs")
        if st.button("Generate ID Cards"):
            ids_list = [ID.strip() for ID in IDs.split(",") if ID.strip()]
            cards = []
            for ID in ids_list:
                data = {
                    'ID': ID,
                    'Division/Section': st.text_input("Division/Section"),
                    'Name': st.text_input("Name"),
                    'University': st.text_input("University"),
                    'Internship Start Date': st.text_input("Internship Start Date"),
                    'Internship End Date': st.text_input("Internship End Date"),
                    'Mobile': st.text_input("Mobile")
                }
                card = generate_card(data, template_path, image_folder, qr_folder)
                if card:
                    st.image(card)
                    cards.append(card)

            if cards:
                pdf_path = "generated_id_cards.pdf"
                pdf_created = create_pdf(cards, pdf_path)
                if pdf_created:
                    display_pdf(pdf_path)

    elif choice == "Generate ID Cards from CSV":
        st.header("Generate ID Cards from CSV")
        uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
        if uploaded_file:
            df = pd.read_csv(uploaded_file)
            AgGrid(df)
            if st.button("Generate ID Cards"):
                cards = []
                for idx, row in df.iterrows():
                    data = {
                        'ID': row.get('ID', ''),
                        'Division/Section': row.get('Division/Section', ''),
                        'Name': row.get('Name', ''),
                        'University': row.get('University', ''),
                        'Internship Start Date': row.get('Internship Start Date', ''),
                        'Internship End Date': row.get('Internship End Date', ''),
                        'Mobile': row.get('Mobile', '')
                    }
                    card = generate_card(data, template_path, image_folder, qr_folder)
                    if card:
                        cards.append(card)

                if cards:
                    pdf_path = "generated_id_cards.pdf"
                    pdf_created = create_pdf(cards, pdf_path)
                    if pdf_created:
                        display_pdf(pdf_path)

if __name__ == "__main__":
    main()
