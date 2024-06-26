import streamlit as st
import pandas as pd
import os
from PIL import Image, ImageDraw, ImageFont
import textwrap
from fpdf import FPDF
import base64
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import dlib
import cv2
import numpy as np

# Initialize dlib's face detector and shape predictor
detector = dlib.get_frontal_face_detector()
predictor_path = "idcard/projectidcard/ritika/downloaded_images/shape_predictor_68_face_landmarks.dat"  # Update with your shape predictor path
predictor = dlib.shape_predictor(predictor_path)

# Function to preprocess image (convert to RGB and detect faces)
def preprocess_image(image_path):
    try:
        input_image = Image.open(image_path)
        final_image = input_image.convert("RGB")
        return final_image
    except Exception as e:
        st.error(f"Error opening image at image_path: {str(e)}")
        return None

# Function to detect and crop face to passport size
def detect_and_crop_face(image_path):
    try:
        img = cv2.imread(image_path)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        faces = detector(gray)

        if len(faces) == 0:
            st.error("No face detected. Please use an image with a clear frontal face.")
            return None
        
        # Assume single face in the image for simplicity
        face = faces[0]
        landmarks = predictor(gray, face)

        # Extract face coordinates
        left = face.left()
        top = face.top()
        right = face.right()
        bottom = face.bottom()

        # Crop and resize face to passport size (144x149)
        cropped_face = img[top:bottom, left:right]
        resized_face = cv2.resize(cropped_face, (144, 149))

        # Convert back to PIL image
        pil_image = Image.fromarray(resized_face)

        return pil_image

    except Exception as e:
        st.error(f"Error detecting and cropping face: {str(e)}")
        return None

# Function to generate ID card with detected and cropped face
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

    preprocessed_pic = preprocess_image(pic_path)
    if preprocessed_pic is None:
        return None
    
    detected_face = detect_and_crop_face(pic_path)
    if detected_face is None:
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
            lines.append(current_line[:-1])  # Exclude the trailing space
            current_line = word + " "

    lines.append(current_line[:-1])  # Include the last line

    centered_lines = [line.center(width) for line in lines]
    centered_text = "\n".join(centered_lines)

    return centered_text

# Function to get the head by division
def get_head_by_division(division_name):
    divisions = {
        "Advanced Information Technologies Group": ["Dr. Sanjay Singh"],
        "Societal Electronics Group": ["Dr. Udit Narayan Pal"],
        "Industrial Automation": ["Dr.S.S.Sadistap"],
        "Vacuum Electronic Devices Group": ["Dr. Sanjay Kr. Ghosh"],
        "High-Frequency Devices & System Group": ["Dr. Ayan Bandhopadhyay"],
        "Semiconductor Sensors & Microsystems Group": ["Dr. Suchandan Pal"],
        "Semiconductor Process Technology Group": ["Dr. Kuldip Singh"],
        "Industrial R & D": ["Mr.Ashok Chauhan"],
        "High Power Microwave Systems Group": ["Dr. Anirban Bera"],
    }

    division_name = division_name.strip().title()

    if division_name in divisions:
        head_names = divisions[division_name]
        return head_names[0]  # Assuming only one head for each division
    else:
        return "Division not found or head information not available."

# Function to create a PDF from the generated ID cards
def create_pdf(cards, output_path):
    pdf = FPDF()
    for card in cards:
        pdf.add_page()
        card_path = f"temp_{card}.png"
        card.save(card_path)
        pdf.image(card_path, x=10, y=10, w=190)
        os.remove(card_path)  # Remove temporary image file
    pdf.output(output_path)
    return output_path

def generate_agrid(data):
    gb = GridOptionsBuilder.from_dataframe(data)
    gb.configure_default_column(editable=True)
    gb.configure_grid_options(domLayout='normal')
    grid_options = gb.build()

    grid_response = AgGrid(
        data,
        gridOptions=grid_options,
        update_mode=GridUpdateMode.MODEL_CHANGED
    )

    return grid_response

def get_binary_file_downloader_html(bin_file, file_label='File'):
    with open(bin_file, 'rb') as f:
        data = f.read()
    bin_str = base64.b64encode(data).decode()
    return f'<a href="data:application/octet-stream;base64,{bin_str}" download="{os.path.basename(bin_file)}">{file_label}</a>'

def main():
    st.title("Automatic ID Card Generation")

    template_path = "idcard/projectidcard/ritika/ST.png"
    image_folder = "idcard/projectidcard/ritika/downloaded_images"
    qr_folder = "idcard/projectidcard/ritika/ST_output_qr_codes"
    output_pdf_path_default = "C:\\Users\\Shree\\Downloads\\generated_id_cards.pdf"  # Default download path

    st.sidebar.header('Manage CSV')

    csv_file = st.sidebar.file_uploader("Upload or Update your CSV file", type=['csv'], key='csv_uploader')

    if csv_file is not None:
        try:
            csv_data = pd.read_csv(csv_file)
            st.sidebar.success('CSV file successfully uploaded/updated.')

            modified_csv = st.sidebar.checkbox('Modify CSV')
            if modified_csv:
                st.subheader('Edit CSV')
                with st.expander("View/Modify CSV"):
                    grid_response = generate_agrid(csv_data)

                    if 'csv_data_updated' in st.session_state and st.session_state['csv_data_updated']:
                        grid_data = grid_response['data']
                        grid_df = pd.DataFrame(grid_data)
                        grid_df.to_csv(csv_file.name, index=False)
                        st.success(f'CSV file "{csv_file.name}" updated successfully.')
                        st.session_state['csv_data_updated'] = False

        except Exception as e:
            st.error(f"Error reading CSV file: {str(e)}")

    st.subheader('Generate ID Cards')
    generate_mode = st.radio("Select ID card generation mode:", ('Individual ID', 'Comma-separated IDs', 'All Students'))

    if generate_mode == 'Individual ID':
        id_input = st.text_input('Enter the ID:')
        if st.button('Generate ID Card'):
            if not id_input.isdigit():
                st.warning('Invalid input. Please enter a valid numeric ID.')
            else:
                selected_data = csv_data[csv_data['ID'] == int(id_input)].iloc[0]
                generated_card = generate_card(selected_data, template_path, image_folder, qr_folder)
                if generated_card:
                    st.image(generated_card, caption=f"Generated ID Card for ID: {id_input}")

    elif generate_mode == 'Comma-separated IDs':
        ids_input = st.text_input('Enter comma-separated IDs:')
        if st.button('Generate ID Cards'):
            id_list = [int(id.strip()) for id in ids_input.split(',') if id.strip().isdigit()]
            generated_cards = []

            for id_input in id_list:
                selected_data = csv_data[csv_data['ID'] == id_input].iloc[0]
                generated_card = generate_card(selected_data, template_path, image_folder, qr_folder)
                if generated_card:
                    generated_cards.append(generated_card)

            if generated_cards:
                st.success(f"Generated {len(generated_cards)} ID cards.")
                for i, card in enumerate(generated_cards):
                    st.image(card, caption=f"Generated ID Card for ID: {id_list[i]}")

                pdf_path = create_pdf(generated_cards, output_pdf_path_default)
                if pdf_path:
                    st.success(f"PDF created successfully.")
                    st.markdown(get_binary_file_downloader_html(pdf_path, 'Download PDF'), unsafe_allow_html=True)
                else:
                    st.error("Failed to create PDF.")

    elif generate_mode == 'All Students':
        st.info("Generating ID cards for all students...")
        generated_cards = []

        for index, data in csv_data.iterrows():
            generated_card = generate_card(data, template_path, image_folder, qr_folder)
            if generated_card:
                generated_cards.append(generated_card)

        if generated_cards:
            st.success(f"Generated {len(generated_cards)} ID cards.")

            pdf_path = create_pdf(generated_cards, output_pdf_path_default)
            if pdf_path:
                st.success(f"PDF created successfully.")
                st.markdown(get_binary_file_downloader_html(pdf_path, 'Download PDF'), unsafe_allow_html=True)
            else:
                st.error("Failed to create PDF.")

if __name__ == "__main__":
    main()
