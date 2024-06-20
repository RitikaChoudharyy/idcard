import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import pandas as pd
import os
import textwrap
from fpdf import FPDF
import fitz
from io import BytesIO
import base64

# Function to generate ID card for an individual
def generate_card(data, template_path, image_folder, qr_folder):
    if not os.path.exists(template_path):
        st.error("Template image not found at the specified location.")
        return None
    
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

    template = Image.open(template_path)
    pic = Image.open(pic_path).resize((144, 145))
    qr = Image.open(qr_path).resize((161, 159))
    
    template.paste(pic, (27, 113, 171, 258))
    template.paste(qr, (497, 109, 658, 268))
    
    draw = ImageDraw.Draw(template)
    font = ImageFont.truetype("C:\\WINDOWS\\FONTS\\ARIAL.TTF", size=18)  # Adjust the font path as needed
    
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
    name_font = ImageFont.truetype("C:\\WINDOWS\\FONTS\\ARIAL.TTF", size=18)  # Adjust the font path as needed
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

# Function to get the head of the division
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
    num_images = len(images)
    rows = (num_images + 3) // 4  # Calculate number of rows needed for the grid
    
    pdf.set_auto_page_break(auto=True, margin=15)
    for i in range(rows):
        pdf.add_page()
        for j in range(4):
            index = i * 4 + j
            if index < num_images:
                x_offset = j * 210  # Adjust the horizontal spacing
                y_offset = i * 297  # Adjust the vertical spacing
                pdf.image(images[index], x=10 + x_offset, y=10 +                y_offset, w=200)
    # Output PDF after adding all pages
    pdf.output(pdf_path)
    return pdf_path

# Function to display the PDF in Streamlit
def display_pdf(pdf_path):
    # Read the PDF file as bytes
    with open(pdf_path, "rb") as file:
        pdf_bytes = file.read()

    # Encode PDF bytes to base64
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

    # Print button
    print_js = f"""
        <script>
            function printPDF() {{
                const linkSource = "data:application/pdf;base64,{b64_pdf}";
                const downloadLink = document.createElement("a");
                downloadLink.href = linkSource;
                downloadLink.download = "generated_id_cards.pdf";
                downloadLink.click();
            }}
        </script>
        <button onclick="printPDF()">Print PDF</button>
    """
    st.markdown(print_js, unsafe_allow_html=True)

# Main Streamlit app
def main():
    st.title("Automatic ID Card Generation")
    
    template_path = "C:\\Users\\Shree\\Desktop\\idcard\\projectidcard\\ritika\\ST.png"
    image_folder = "C:\\Users\\Shree\\Desktop\\idcard\\projectidcard\\ritika\\downloaded_images"
    qr_folder = "C:\\Users\\Shree\\Desktop\\idcard\\projectidcard\\ritika\\ST_output_qr_codes"
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

        # Button to generate ID cards
        if st.button("Generate ID Cards"):
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

