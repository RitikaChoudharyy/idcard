import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import pandas as pd
import os
import textwrap
from fpdf import FPDF
import fitz  # PyMuPDF
import base64

# Function to generate ID card
def generate_card(data, template_path, image_folder, qr_folder):
    global generated_ids
    pic_id = str(data.get('ID', ''))
    
    # Check if ID already generated to avoid duplicates
    if pic_id in generated_ids:
        st.warning(f"Skipping duplicate ID: {pic_id}")
        return None
    
    generated_ids.append(pic_id)
    
    if not os.path.exists(template_path):
        st.error(f"Template image not found at the specified location: {template_path}")
        st.stop()
    
    pic_path = os.path.join(image_folder, f"{pic_id}.jpg")
    if not os.path.exists(pic_path):
        st.error(f"Image not found for ID: {pic_id} at path: {pic_path}")
        return None
    
    qr_path = os.path.join(qr_folder, f"{pic_id}.png")
    if not os.path.exists(qr_path):
        st.error(f"QR code not found for ID: {pic_id} at path: {qr_path}")
        return None

    # Preprocess the image
    try:
        preprocessed_pic = preprocess_image(pic_path)
        preprocessed_pic = preprocessed_pic.resize((144, 145))
    except Exception as e:
        st.error(f"Error preprocessing image for ID: {pic_id}. Error: {str(e)}")
        return None

    try:
        template = Image.open(template_path)
        qr = Image.open(qr_path).resize((161, 159))
        
        template.paste(preprocessed_pic, (27, 113, 171, 258))
        template.paste(qr, (497, 109, 658, 268))
        
        draw = ImageDraw.Draw(template)
        
        # Load Arial font with fallback to default system font
        try:
            font_path = "C:\\WINDOWS\\FONTS\\ARIAL.TTF"
            name_font = ImageFont.truetype(font_path, size=18)
        except IOError:
            name_font = ImageFont.load_default()  # Fallback to default font if Arial is not available
        
        font_size = 18
        
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
        
        # Adjusted for name wrapping
        wrapped_name = center_align_text_wrapper(data['Name'], width=22)
        
        # Get the text size using ImageFont.textbbox()
        name_bbox = name_font.getbbox(wrapped_name)
        name_width = name_bbox[2] - name_bbox[0]
        
        # Calculate the x-coordinate to center the text name
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
def create_pdf(images, pdf_path):
    pdf = FPDF()
    cards_per_page = 8  # 2x4 grid
    num_pages = -(-len(images) // cards_per_page)  # Ceiling division to get the number of pages needed
    
    for page_num in range(num_pages):
        pdf.add_page()
        
        for i in range(cards_per_page):
            card_index = page_num * cards_per_page + i
            if card_index < len(images):
                card = images[card_index]
                temp_image_path = f"temp_image_{card_index}.jpg"
                # Ensure the image is in RGB mode before saving as JPEG
                if card.mode == 'RGBA':
                    card = card.convert('RGB')
                card.save(temp_image_path)
                
                # Calculate x, y position for each card in the grid
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

    # Display PDF in an iframe
    pdf_display = f'<iframe src="data:application/pdf;base64,{b64_pdf}" width="700" height="1000" type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)

    # Download button
    st.download_button(
        label="Download PDF",
        data=pdf_bytes,
        file_name="generated_id_cards.pdf",
        mime="application/pdf"
    )

    # Display ID card images directly
    for page in doc:
        for img in page.get_images(full=True):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base64.b64encode(base_image["image"])
            st.image(base_image["image"], caption="Generated ID Card")

def main():
    st.title("Automatic ID Card Generation")
    
    # Hardcoded paths (adjust as per your actual folder structure)
    template_path = r"idcard/projectidcard/ritika/ST.png"
    image_folder = r"idcard/projectidcard/ritika/downloaded_images"
    qr_folder = r"idcard/projectidcard/ritika/ST_output_qr_codes"
    output_pdf_path = r"C:\Users\Shree\Desktop\generated_id_cards.pdf"

    # Upload CSV file with data
    st.sidebar.header('Upload CSV')
    csv_file = st.sidebar.file_uploader("Upload your CSV file", type=['csv'])

    if csv_file is not None:
        try:
            data = pd.read_csv(csv_file)
        except Exception as e:
            st.sidebar.error(f"Error reading CSV file: {str(e)}")
            return

        # Display the uploaded data on the sidebar
        st.sidebar.subheader('Uploaded Data')
        st.sidebar.write(data)

        # Button to browse downloaded images folder
        st.sidebar.header('Browse Downloaded Images Folder')
        image_folder_path = st.sidebar.text_input('Enter path to downloaded images folder')
        if st.sidebar.button('Browse'):
            if os.path.exists(image_folder_path):
                image_folder = image_folder_path
                st.sidebar.success(f"Updated image folder path: {image_folder}")
            else:
                st.sidebar.error("Path does not exist!")

        # Generate ID cards
        st.subheader('Generate ID Cards')
        generate_mode = st.radio("Select ID card generation mode:", ('Individual ID', 'Comma-separated IDs', 'All Students'))

        if generate_mode == 'Individual ID':
            id_input = st.text_input('Enter ID:', value='')
            if st.button('Generate ID Card'):
                selected_data = data[data['ID'] == int(id_input)]
                if len(selected_data) == 0:
                    st.warning(f"No data found for ID: {id_input}")
                else:
                    generated_images = []
                    for index, row in selected_data.iterrows():
                        card = generate_card(row, template_path, image_folder, qr_folder)
                        if card is not None:
                            generated_images.append(card)
                    if generated_images:
                        st.success('ID card generated successfully!')
                        for image in generated_images:
                            st.image(image, use_column_width=True)
                    else:
                        st.warning('No ID card generated.')

        elif generate_mode == 'Comma-separated IDs':
            ids_input = st.text_area('Enter comma-separated IDs:', value='')
            if st.button('Generate ID Cards'):
                ids_list = [int(id.strip()) for id in ids_input.split(',') if id.strip().isdigit()]
                if not ids_list:
                    st.warning('Invalid input. Please enter valid comma-separated IDs.')
                else:
                    generated_images = []
                    for id_input in ids_list:
                        selected_data = data[data['ID'] == id_input]
                        if len(selected_data) == 0:
                            st.warning(f"No data found for ID: {id_input}")
                        else:
                            for index, row in selected_data.iterrows():
                                card = generate_card(row, template_path, image_folder, qr_folder)
                                if card is not None:
                                    generated_images.append(card)
                    if generated_images:
                        st.success('ID cards generated successfully!')
                        for image in generated_images:
                            st.image(image, use_column_width=True)
                    else:
                        st.warning('No ID cards generated.')

        elif generate_mode == 'All Students':
            if st.button('Generate ID Cards for All Students'):
                generated_images = []
                for index, row in data.iterrows():
                    card = generate_card(row, template_path, image_folder, qr_folder)
                    if card is not None:
                        generated_images.append(card)
                if generated_images:
                    st.success('ID cards generated successfully!')
                    for image in generated_images:
                        st.image(image, use_column_width=True)
                else:
                    st.warning('No ID cards generated.')

        # Create PDF from generated ID cards
        st.subheader('Download PDF')
        pdf_download_button = st.button('Download PDF')
        
        if pdf_download_button:
            try:
                pdf_path = create_pdf(generated_images, output_pdf_path)
                st.success(f'PDF successfully generated: [{pdf_path}]')

                # Display PDF and download button
                display_pdf(pdf_path)

            except Exception as e:
                st.error(f'Error generating PDF: {str(e)}')

if __name__ == '__main__':
    main()
