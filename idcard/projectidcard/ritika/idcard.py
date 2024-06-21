import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import pandas as pd
import os
import textwrap
from fpdf import FPDF
import fitz  # PyMuPDF
import base64
from rembg import remove  # Assuming this library is correctly installed

# Function to preprocess image (remove background and convert to RGB)
def preprocess_image(image_path):
    input_image = Image.open(image_path)
    output_image = remove(input_image)

    # Convert the background to white
    white_bg = Image.new("RGBA", output_image.size, "WHITE")
    final_image = Image.alpha_composite(white_bg, output_image)

    # Convert to RGB mode
    final_image = final_image.convert("RGB")

    return final_image

# Function to generate ID card
# Function to generate ID card
def generate_card(data, template_path, image_folder, qr_folder):
    st.write(f"Checking template path: {template_path}")
    if not os.path.exists(template_path):
        st.error(f"Template image not found at the specified location: {template_path}")
        st.stop()
    
    pic_id = str(data.get('ID', ''))
    if not pic_id:
        st.warning(f"Skipping record with missing ID: {data}")
        return None
    
    pic_path = os.path.join(image_folder, f"{pic_id}.jpg")
    if not os.path.exists(pic_path):
        st.error(f"Image not found for ID: {pic_id} at path: {pic_path}")
        return None
    
    qr_path = os.path.join(qr_folder, f"{pic_id}.png")
    if not os.path.exists(qr_path):
        st.error(f"QR code not found for ID: {pic_id} at path: {qr_path}")
        return None

    # Preprocess the image
    preprocessed_pic = preprocess_image(pic_path)
    preprocessed_pic = preprocessed_pic.resize((144, 145))

    template = Image.open(template_path)
    qr = Image.open(qr_path).resize((161, 159))
    
    template.paste(preprocessed_pic, (27, 113, 171, 258))
    template.paste(qr, (497, 109, 658, 268))
    
    draw = ImageDraw.Draw(template)
    # Adjust the font path to match your environment
    font_path = "C:\\WINDOWS\\FONTS\\ARIAL.TTF"  # Adjust the path based on your environment

    # Check if the font file exists
if not os.path.exists(font_path):
    raise FileNotFoundError(f"Font file not found: {font_path}")
try:
    font = ImageFont.truetype(font_path, size=18)
except OSError as e:
    st.error(f"Error loading font: {e}")
    st.stop()  # Stop Streamlit execution in case of error

    font = ImageFont.truetype(font_path, size=18)
    
    wrapped_div = textwrap.fill(str(data['Division/Section']), width=22).title()
    draw.text((311, 121), wrapped_div, font=font, fill='black')
    draw.text((200, 356), data['University '], font=font, fill='black')
    
    division_input = data['Division/Section']
    head_name = get_head_by_division(division_input)
    
    wrapped_supri = textwrap.fill(str(head_name), width=20).title()
    draw.text((311, 170), wrapped_supri.title(), font=font, fill='black')
    
    draw.text((305, 219), data['Internship Start Date'], font=font, fill='black')
    draw.text((303, 266), data['Internship End Date'], font=font, fill='black')
    draw.text((300, 312), str(data['Mobile']), font=font, fill='black')
    draw.text((621, 283), str(data['ID']), font=font, fill='black')

    # Adjusted for name wrapping
    name_font = ImageFont.truetype(font_path, size=18)
    wrapped_name = center_align_text_wrapper(data['Name'], width=22)
    
    # Get the text size using ImageFont.textbbox()
    name_bbox = name_font.getbbox(wrapped_name)
    name_width = name_bbox[2] - name_bbox[0]
    
    # Calculate the x-coordinate to center the text name
    center_x = ((198 - name_width) / 2 )
    draw.text((center_x, 260), wrapped_name.title(), font=name_font, fill='black')
    
    return template


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
    print_js = """
    <script>
        // Your JavaScript code here
        console.log("Hello from JavaScript!");
    </script>
    """
    st.markdown(print_js, unsafe_allow_html=True)

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
    
    template_path = "idcard/projectidcard/ritika/ST.png"
    image_folder = "idcard/projectidcard/ritika/downloaded_images"
    qr_folder = "idcard/projectidcard/ritika/ST_output_qr_codes"
    output_pdf_path = "C:\\Users\\Shree\\Desktop\\generated_id_cards.pdf"

    # File uploader for CSV files
    uploaded_file = st.file_uploader("Upload CSV file", type=["csv"])

    if uploaded_file is not None:
        # Read the uploaded CSV file into a DataFrame
        df = pd.read_csv(uploaded_file, converters={'ID': str})

        # Check for duplicates and remove them
        df = df.drop_duplicates()

        # Display the uploaded data
        st.write("Uploaded CSV file:")
        edited_data = st.data_editor(df)
        st.write(df)

        # Get student ID for individual ID card generation
        student_id = st.text_input("Enter Student ID for Individual ID Card Generation")

        # Button to generate ID card for a specific student
        if st.button("Generate ID Card for Individual Student"):
            if student_id:
                student_data = df[df['ID'] == student_id]
                if not student_data.empty:
                    card = generate_card(student_data.iloc[0], template_path, image_folder, qr_folder)
                    if card:
                        pdf_path = create_pdf([card], output_pdf_path)
                        st.success(f"PDF generated successfully! Check the '{output_pdf_path}' file.")
                        display_pdf(pdf_path)
                else:
                    st.error(f"No student found with ID: {student_id}")
            else:
                st.error("Please enter a Student ID")

        # Button to generate ID cards for all students
        if st.button("Generate ID Cards for All Students"):
            images = []
            records = edited_data.to_dict(orient='records')
            for record in records:
                card = generate_card(record, template_path, image_folder, qr_folder)
                if card:
                    images.append(card)

            # Create and display the PDF
            pdf_path = create_pdf(images, output_pdf_path)
            st.success(f"PDF generated successfully! Check the '{output_pdf_path}' file.")
            display_pdf(pdf_path)

if __name__ == "__main__":
    main()

