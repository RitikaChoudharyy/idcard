import streamlit as st
import pandas as pd
import os
from PIL import Image, ImageDraw, ImageFont
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
        st.error(f"Error opening image at image_path: {str(e)}")
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

def main():
    st.title("Automatic ID Card Generation")
    
    # Update these paths according to your file locations
    template_path = "idcard/projectidcard/ritika/ST.png"
    image_folder = "idcard/projectidcard/ritika/downloaded_images"
    qr_folder = "idcard/projectidcard/ritika/ST_output_qr_codes"
    output_pdf_path = "C:\\Users\\Shree\\Desktop\\generated_id_cards.pdf"

    # Sidebar for CSV management
    st.sidebar.header('Manage CSV')
    csv_file = st.sidebar.file_uploader("Upload or Update your CSV file", type=['csv'], key='csv_uploader')

    if csv_file is not None:
        try:
            csv_data = pd.read_csv(csv_file)
            st.sidebar.success('CSV file successfully uploaded/updated.')

            st.sidebar.subheader('CSV Data Preview')
            st.sidebar.write(csv_data)

            modified_csv = st.sidebar.checkbox('Modify CSV')

            if modified_csv:
                with st.sidebar:
                    st.title('Edit CSV')
                    df = csv_data.copy()
                    df_edited = st.dataframe(df)

                    if st.button('Save Changes'):
                        df_edited.to_csv(csv_file.name, index=False)
                        st.success(f'CSV file "{csv_file.name}" updated successfully.')

            # Main content area
            col1, col2 = st.columns(2)

            # Generate ID cards
            with col1:
                st.subheader('Generate ID Cards')
                generate_mode = st.radio("Select ID card generation mode:", ('Individual ID', 'Comma-separated IDs', 'All Students'))

                if generate_mode == 'Individual ID':
                    id_input = st.text_input('Enter the ID:')
                    if st.button('Generate ID Card'):
                        if not id_input.isdigit():
                            st.warning('Invalid input. Please enter a valid numeric ID.')
                        else:
                            selected_data = csv_data[csv_data['ID'] == int(id_input)]
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
                                    selected_data = csv_data[csv_data['ID'] == int(id_input)]
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
                        for index, row in csv_data.iterrows():
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

        except pd.errors.EmptyDataError:
            st.error('CSV file is empty or not loaded correctly. Please upload a valid CSV file.')
        except Exception as e:
            st.error(f'An unexpected error occurred: {str(e)}')

if __name__ == "__main__":
    main()
