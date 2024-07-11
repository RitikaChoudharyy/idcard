
import streamlit as st
import pandas as pd
import os
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
        
def main():
    # Streamlit setup
    st.title("Automatic ID Card Generation")

    # Update these paths according to your file locations
    template_path = "idcard/projectidcard/ritika/ST.png"
    image_folder = "idcard/projectidcard/ritika/downloaded_images"
    qr_folder = "idcard/projectidcard/ritika/ST_output_qr_codes"
    output_pdf_path_default = "C:\\Users\\Shree\\Downloads\\generated_id_cards.pdf"  # Default download path

    # Sidebar for managing CSV
    st.sidebar.header('Manage CSV')

    # File uploader in sidebar
    csv_file = st.sidebar.file_uploader("Upload or Update your CSV file", type=['csv'], key='csv_uploader')

    if csv_file is not None:
        try:
            csv_data = pd.read_csv(csv_file)
            st.sidebar.success('CSV file successfully uploaded/updated.')

            # Checkbox for modifying CSV in sidebar
            modified_csv = st.sidebar.checkbox('Modify CSV')
            if modified_csv:
                st.subheader('Edit CSV')
                # Display editable DataFrame below the checkbox
                with st.expander("View/Modify CSV"):
                    grid_response = AgGrid(
                        csv_data,
                        editable=True,
                        height=400,
                        fit_columns_on_grid_load=True,
                    )
                    df_edited = grid_response['data']

                    # Automatically save changes to CSV when data is edited
                    if st.session_state.get('csv_data_updated', False):
                        df_edited.to_csv(csv_file.name, index=False)
                        st.success(f'CSV file "{csv_file.name}" updated successfully.')
                        st.session_state['csv_data_updated'] = False  # Reset the flag

                    # Store initial state of csv_data in session state
                    if 'csv_data' not in st.session_state:
                        st.session_state['csv_data'] = csv_data

                    # Check for changes in data and update session state if needed
                    if not df_edited.equals(st.session_state['csv_data']):
                        st.session_state['csv_data_updated'] = True
                        st.session_state['csv_data'] = df_edited.copy()

                    # Button to manually save changes
                    if st.button('Save Changes'):
                        df_edited.to_csv(csv_file.name, index=False)
                        st.success(f'CSV file "{csv_file.name}" updated successfully.')

        except Exception as e:
            st.error(f"Error reading CSV file: {str(e)}")

    # Section to generate ID cards
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

                # Create PDF of generated ID cards
                pdf_path = create_pdf(generated_cards, output_pdf_path_default)
                if pdf_path:
                    st.success(f"PDF created successfully.")
                    # Display download button for the PDF
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

            # Create PDF of generated ID cards
            pdf_path = create_pdf(generated_cards, output_pdf_path_default)
            if pdf_path:
                st.success(f"PDF created successfully.")
                # Display download button for the PDF
                st.markdown(get_binary_file_downloader_html(pdf_path, 'Download PDF'), unsafe_allow_html=True)
            else:
                st.error("Failed to create PDF.")

def get_binary_file_downloader_html(bin_file, file_label='File'):
    with open(bin_file, 'rb') as f:
        data = f.read()
    bin_str = base64.b64encode(data).decode()
    return f'<a href="data:application/octet-stream;base64,{bin_str}" download="{os.path.basename(bin_file)}">{file_label}</a>'

if __name__ == "__main__":
    main()
