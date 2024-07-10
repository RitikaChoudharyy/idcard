import streamlit as st
import pandas as pd
import os
from PIL import Image, ImageDraw, ImageFont
import textwrap
import cv2
import numpy as np
from rembg import remove
import dlib
from fpdf import FPDF
import base64
from st_aggrid import AgGrid
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch, mm
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
        st.error(f"PDF file '{pdf_path}' not found.")
    except Exception as e:
        st.error(f"Error displaying PDF: {str(e)}")

def main():
    # Streamlit setup
    st.title("Automatic ID Card Generation")

    st.sidebar.header("Options")
    options = ["Upload Excel File", "View Sample Data"]
    choice = st.sidebar.selectbox("Choose an option", options)

    if choice == "Upload Excel File":
        st.subheader("Upload Excel File")
        excel_file = st.file_uploader("Choose an Excel file", type=["xlsx"])

        if excel_file is not None:
            try:
                df = pd.read_excel(excel_file)
                st.success("Excel file uploaded successfully!")
                st.dataframe(df.head())  # Display the first few rows of the dataframe

                template_path = st.text_input("Enter the path to the ID card template image")
                image_folder = st.text_input("Enter the folder path containing the images")
                qr_folder = st.text_input("Enter the folder path containing the QR codes")
                output_pdf_path = st.text_input("Enter the path for the output PDF file", "output_id_cards.pdf")

                if st.button("Generate ID Cards"):
                    if not template_path or not image_folder or not qr_folder or not output_pdf_path:
                        st.error("Please provide all the required paths.")
                    else:
                        try:
                            generated_images = []
                            for _, row in df.iterrows():
                                card = generate_card(row, template_path, image_folder, qr_folder)
                                if card:
                                    img_path = f"{image_folder}/{row['ID']}_generated.jpg"
                                    card.save(img_path)
                                    generated_images.append(img_path)

                            if generated_images:
                                pdf_path = create_pdf(generated_images, output_pdf_path)
                                if pdf_path:
                                    st.success("ID cards generated and saved successfully!")
                                    display_pdf(pdf_path)
                                else:
                                    st.error("Failed to create PDF.")
                            else:
                                st.error("No ID cards were generated. Please check the logs for more details.")
                        except Exception as e:
                            st.error(f"Error generating ID cards: {str(e)}")
                            logging.error(f"Error generating ID cards: {str(e)}")

            except Exception as e:
                st.error(f"Error uploading Excel file: {str(e)}")
                logging.error(f"Error uploading Excel file: {str(e)}")

    elif choice == "View Sample Data":
        st.subheader("Sample Data")
        sample_data = {
            "ID": [1, 2, 3],
            "Name": ["John Doe", "Jane Smith", "Alice Johnson"],
            "Division/Section": ["Advanced Information Technologies Group", "Societal Electronics Group", "Industrial Automation"],
            "Internship Start Date": ["2024-01-01", "2024-02-01", "2024-03-01"],
            "Internship End Date": ["2024-06-01", "2024-07-01", "2024-08-01"],
            "Mobile": ["1234567890", "0987654321", "1122334455"],
            "University": ["University A", "University B", "University C"]
        }
        df_sample = pd.DataFrame(sample_data)
        AgGrid(df_sample)  # Display sample data using st_aggrid

if __name__ == "__main__":
    main()
