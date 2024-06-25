import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import pandas as pd
import os
import textwrap
from fpdf import FPDF
import fitz  # PyMuPDF
import base64

# Function to preprocess image (convert to RGB)
def preprocess_image(image_path):
    try:
        input_image = Image.open(image_path)
        final_image = input_image.convert("RGB")
        return final_image
    except Exception as e:
        st.error(f"Error opening image at {image_path}: {str(e)}")
        return None

# Function to generate ID card
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
            font_path = "C:\\WINDOWS\\FONTS\\ARIAL.TTF"
            name_font = ImageFont.truetype(font_path, size=18)
        except IOError:
            name_font = ImageFont.load_default()
        
        wrapped_div = textwrap.fill(str(data['Division/Section']), width=22).title()
        draw.text((311, 121), wrapped_div, font=name_font, fill='black')
        draw.text((200, 356), data['University '], font=name_font, fill='black')
        
        division_input = data['Division/Section']
        head_name = get_head_by_division(division_input)
        
        wrapped_supri = textwrap.fill(str(head_name), width=20).title()
        draw.text((311, 170), wrapped_supri, font=name_font, fill='black')
        
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

# Function to create a PDF from the generated ID cards
def create_pdf(images, pdf_path):
    pdf = FPDF()
    cards_per_page = 8
    num_pages = -(-len(images) // cards_per_page)
    
    for page_num in range(num_pages):
        pdf.add_page()
        
        for i in range(cards_per_page):
            card_index = page_num * cards_per_page + i
            if card_index < len(images):
                card = images[card_index]
                temp_image_path = f"temp_image_{card_index}.jpg"
                if card.mode == 'RGBA':
                    card = card.convert('RGB')
                card.save(temp_image_path)
                
                col = i % 4
                row = i // 4
                x_offset = col * (pdf.w / 4 - 10)
                y_offset = row * (pdf.h / 2 - 10)
                
                pdf.image(temp_image_path, x=5 + x_offset, y=5 + y_offset, w=pdf.w / 4 - 10)
                os.remove(temp_image_path)
    
    pdf.output(pdf_path)
    return pdf_path

# Function to display the PDF in Streamlit
def display_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    pdf_bytes = doc.convert_to_pdf()
    b64_pdf = base64.b64encode(pdf_bytes).decode()

    pdf_display = f'<iframe src="data:application/pdf;base64,{b64_pdf}" width="700" height="1000" type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)

    st.download_button(
        label="Download PDF",
        data=pdf_bytes,
        file_name="generated_id_cards.pdf",
        mime="application/pdf"
    )

    for page in doc:
        for img in page.get_images(full=True):
            xref = img[0]
            base_image = doc.extract_image(xref)
            st.image(base_image["image"], caption="Generated ID Card")

def main():
    st.title("Automatic ID Card Generation")
    
    # Update these paths according to your file locations
    template_path = "idcard/projectidcard/ritika/ST.png"
    image_folder = "idcard/projectidcard/ritika/downloaded_images"
    qr_folder = "idcard/projectidcard/ritika/ST_output_qr_codes"
    output_pdf_path = "C:\\Users\\Shree\\Desktop\\generated_id_cards.pdf"

    st.sidebar.header('Upload CSV')
    csv_file = st.sidebar.file_uploader("Upload your CSV file", type=['csv'])

    if csv_file is not None:
        try:
            data = pd.read_csv(csv_file)
        except Exception as e:
            st.sidebar.error(f"Error reading CSV file: {str(e)}")
            return

        st.sidebar.subheader('Uploaded Data')
        st.sidebar.write(data)

        st.subheader('Generate ID Cards')
        generate_mode = st.radio("Select ID card generation mode:", ('Individual ID', 'Comma-separated IDs', 'All Students'))

        if generate_mode == 'Individual ID':
            id_input = st.text_input('Enter the ID:')
            if st.button('Generate ID Card'):
                if not id_input.isdigit():
                    st.warning('Invalid input. Please enter a valid numeric ID.')
                else:
                    selected_data = data[data['ID'] == int(id_input)]
                    if selected_data.empty:
                        st.warning(f"No data found for ID: {id_input}")
                    else:
                        generated_images = []
                        for index, row in selected_data.iterrows():
                            card = generate_card(row, template_path, image_folder, qr_folder)
                            if card is not None:
                                generated_images.append(card)
                        
                        if generated_images:
                            st.success('ID card(s) generated successfully!')
                            pdf_download_button = st.button('Download PDF')

                            if pdf_download_button:
                                try:
                                    pdf_path = create_pdf(generated_images, output_pdf_path)
                                    st.success(f'PDF successfully generated: [{pdf_path}]')
                                    display_pdf(pdf_path)
                                except Exception as e:
                                    st.error(f'Error generating PDF: {str(e)}')

                            for image in generated_images:
                                st.image(image, use_column_width=True)
                        else:
                            st.warning('No ID card(s) generated.')

        elif generate_mode == 'Comma-separated IDs':
            ids_input = st.text_area('Enter comma-separated IDs:', value='')
            if st.button('Generate ID Cards'):
                ids_list = [id.strip() for id in ids_input.split(',') if id.strip().isdigit()]
                if not ids_list:
                    st.warning('Invalid input. Please enter valid comma-separated IDs.')
                else:
                    generated_images = []
                    for id_input in ids_list:
                        try:
                            selected_data = data[data['ID'] == int(id_input)]
                        except ValueError:
                            st.warning(f"Skipping invalid ID: {id_input}. Please enter valid integer IDs.")
                            continue
                        
                        if selected_data.empty:
                            st.warning(f"No data found for ID: {id_input}")
                        else:
                            for index, row in selected_data.iterrows():
                                card = generate_card(row, template_path, image_folder, qr_folder)
                                if card is not None:
                                    generated_images.append(card)
                    
                    if generated_images:
                        st.success('ID card(s) generated successfully!')
                        pdf_download_button = st.button('Download PDF')

                        if pdf_download_button:
                            try:
                                pdf_path = create_pdf(generated_images, output_pdf_path)
                                st.success(f'PDF successfully generated: [{pdf_path}]')
                                display_pdf(pdf_path)
                            except Exception as e:
                                st.error(f'Error generating PDF: {str(e)}')

                        for image in generated_images:
                            st.image(image, use_column_width=True)
                    else:
                        st.warning('No ID card(s) generated.')

        elif generate_mode == 'All Students':
            if st.button('Generate ID Cards for All Students'):
                generated_images = []
                for index, row in data.iterrows():
                    card = generate_card(row, template_path, image_folder, qr_folder)
                    if card is not None:
                        generated_images.append(card)
                
                if generated_images:
                    st.success('ID card(s) generated successfully!')
                    pdf_download_button = st.button('Download PDF')

                    if pdf_download_button:
                        try:
                            pdf_path = create_pdf(generated_images, output_pdf_path)
                            st.success(f'PDF successfully generated: [{pdf_path}]')
                            display_pdf(pdf_path)
                        except Exception as e:
                            st.error(f'Error generating PDF: {str(e)}')

                    for image in generated_images:
                        st.image(image, use_column_width=True)
                else:
                    st.warning('No ID card(s) generated.')

if __name__ == "__main__":
    main()
