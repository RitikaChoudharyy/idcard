import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import pandas as pd
import os
import textwrap
from fpdf import FPDF
import fitz  # PyMuPDF
import base64

# Import rembg for background removal if available
try:
    from rembg import remove  # Assuming this library is correctly installed
    REMBG_AVAILABLE = True
except ImportError:
    REMBG_AVAILABLE = False
    st.warning("Background removal library 'rembg' is not available. ID cards will be generated without background removal.")

# Function to preprocess image (remove background and convert to RGB), handle if rembg is not available
def preprocess_image(image_path):
    input_image = Image.open(image_path)
    
    if REMBG_AVAILABLE:
        output_image = remove(input_image)
        # Convert the background to white
        white_bg = Image.new("RGBA", output_image.size, "WHITE")
        final_image = Image.alpha_composite(white_bg, output_image)
    else:
        # Convert the image to RGB mode without background removal
        final_image = input_image.convert("RGB")
    
    return final_image

# Function to generate ID card
def generate_card(data, template_path, image_path, qr_path):
    try:
        preprocessed_pic = preprocess_image(image_path)
        preprocessed_pic = preprocessed_pic.resize((144, 145))
    except Exception as e:
        st.error(f"Error preprocessing image: {str(e)}")
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
        st.error(f"Error generating card: {str(e)}")
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

# Main Streamlit app
def main():
    st.title("Automatic ID Card Generation")
    
    # Upload CSV file
    st.subheader("Upload CSV File")
    uploaded_file = st.file_uploader("Choose a CSV file", type=["csv"])

    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            
            # Check if required fields are present
            required_fields = ['ID', 'Name', 'Division/Section', 'University', 'Internship Start Date',
                               'Internship End Date', 'Mobile']
            if not all(field in df.columns for field in required_fields):
                st.error("CSV file is missing required fields.")
                return

            # Select images folder
            st.subheader("Select Images Folder")
            images_folder = st.file_uploader("Choose a folder containing images", type=["jpg", "png"], accept_multiple_files=True)

            # Select QR codes folder
            st.subheader("Select QR Codes Folder")
            qr_folder = st.file_uploader("Choose a folder containing QR codes", type=["png"], accept_multiple_files=True)

            if images_folder and qr_folder:
                images_paths = {image.name: image for image in images_folder}
                                qr_paths = {qr.name: qr for qr in qr_folder}

                # Sidebar selection for ID cards generation
                st.sidebar.title("Select Student IDs for ID Cards")
                st.sidebar.markdown("You can select individual IDs, a comma-separated list, or generate for all student IDs.")
                options = ['All'] + df['ID'].astype(str).tolist()
                selected_ids = st.sidebar.multiselect('Select Student IDs', options=options, default='All')

                # Generate ID cards button
                if st.button("Generate ID Cards"):
                    if 'All' in selected_ids:
                        selected_rows = df
                    else:
                        selected_ids = [int(id.strip()) for id in selected_ids if id.strip().isdigit()]
                        selected_rows = df[df['ID'].isin(selected_ids)]

                    images = []
                    for index, row in selected_rows.iterrows():
                        student_id = row['ID']
                        image_path = images_paths.get(f"{student_id}.jpg", None)
                        qr_path = qr_paths.get(f"{student_id}.png", None)
                        if image_path and qr_path:
                            card = generate_card(row, template_path, image_path, qr_path)
                            if card:
                                images.append(card)
                        else:
                            st.warning(f"Image or QR code missing for student ID: {student_id}")

                    if images:
                        pdf_path = "generated_id_cards.pdf"
                        pdf_path = create_pdf(images, pdf_path)
                        display_pdf(pdf_path)
                    else:
                        st.warning("No ID cards were generated. Please check the input files.")

        except Exception as e:
            st.error(f"Error reading CSV file: {str(e)}")

if __name__ == "__main__":
    main()

