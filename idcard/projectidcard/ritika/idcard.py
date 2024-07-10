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
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io
import gspread

# Set up logging
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

# Function to generate card using fetched image and data
def generate_card(data, template_path, image_paths, qr_folder):
    pic_id = str(data.get('ID', ''))
    if not pic_id:
        st.warning(f"Skipping record with missing ID: {data}")
        return None
    
    pic_path = [path for path in image_paths if pic_id in path]
    if not pic_path:
        st.error(f"Image not found for ID: {pic_id}")
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

# Function to create PDF from generated ID cards
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

# Function to display download link for generated PDF
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

# Function to download images from Google Drive using file URLs in Google Sheet
def download_images_from_drive(credentials_path, sheet_id, output_folder):
    try:
        # Authenticate with Google Drive API using service account credentials
        credentials = service_account.Credentials.from_service_account_file(credentials_path, scopes=['https://www.googleapis.com/auth/drive'])
        drive_service = build('drive', 'v3', credentials=credentials)

        # Connect to the Google Sheet using gspread
        gc = gspread.authorize(credentials)
        worksheet = gc.open_by_key(sheet_id).sheet1  # Open the specified sheet

        # Get image URLs from the second column (skip header row)
        image_urls = worksheet.col_values(2)[1:]

        # Ensure the output folder exists
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        downloaded_image_paths = []

        for index, url in enumerate(image_urls):
            try:
                # Extract file ID from URL
                file_id = url.split("/")[-2]

                # Request the file metadata and download
                request = drive_service.files().get_media(fileId=file_id)
                fh = io.BytesIO()
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()

                # Save the downloaded image
                image_path = os.path.join(output_folder, f"{index + 1}.jpg")
                with open(image_path, 'wb') as f:
                    f.write(fh.getvalue())

                st.write(f"Downloaded image {index + 1}/{len(image_urls)}")
                downloaded_image_paths.append(image_path)
            
            except Exception as e:
                st.error(f"Error downloading image from URL {url}: {str(e)}")
                logging.error(f"Error downloading image from URL {url}: {str(e)}")

        return downloaded_image_paths

    except Exception as e:
        st.error(f"Error downloading images from Google Drive: {str(e)}")
        logging.error(f"Error downloading images from Google Drive: {str(e)}")
        return []

# Main Streamlit app code
def main():
    st.title("Intern ID Card Generator")

    # Sidebar - file upload and generation options
    st.sidebar.header("Generate ID Cards")

    # Select an option
    generation_option = st.sidebar.selectbox("Select an option", ("Generate ID Cards", "Download Images"))

    if generation_option == "Generate ID Cards":
        st.subheader("Generate ID Cards")

        # Select template and folders
        template_path = st.sidebar.file_uploader("Upload Template", type=["jpg", "jpeg", "png"])
        image_folder = st.sidebar.text_input("Image Folder Path")
        qr_folder = st.sidebar.text_input("QR Folder Path")

        # Check if template and folders are selected
        if template_path and image_folder and qr_folder:
            # Load data from Google Sheet and Download Images
            credentials_path = st.sidebar.file_uploader("Upload Google Service Account Credentials", type=["json"])
            sheet_id = st.sidebar.text_input("Google Sheet ID")
            if credentials_path and sheet_id:
                try:
                    output_folder = "downloaded_images"
                    downloaded_image_paths = download_images_from_drive(credentials_path, sheet_id, output_folder)
                except Exception as e:
                    st.error(f"Error downloading images: {str(e)}")

            # Display grid with data
            if os.path.exists(image_folder) and os.path.exists(qr_folder):
                data_path = st.sidebar.file_uploader("Upload Data File", type=["csv", "xlsx"])
                if data_path:
                    try:
                        data = pd.read_excel(data_path)  # Adjust if CSV is used
                        AgGrid(data)

                        # Generate ID cards
                        st.subheader("Generated ID Cards")
                        images = []
                        for _, row in data.iterrows():
                            card = generate_card(row, template_path, downloaded_image_paths, qr_folder)
                            if card:
                                images.append(card)

                        # Create PDF
                        pdf_path = "generated_id_cards.pdf"
                        pdf_path = create_pdf(images, pdf_path)
                        if pdf_path:
                            st.success(f"PDF generated successfully! Click below to download.")
                            display_pdf(pdf_path)

                    except Exception as e:
                        st.error(f"Error processing data file: {str(e)}")
                        logging.error(f"Error processing data file: {str(e)}")

            else:
                st.warning("Please provide valid paths for Image and QR folders.")
        
        else:
            st.warning("Please upload Template and provide valid paths for Image and QR folders.")
    
    elif generation_option == "Download Images":
        st.subheader("Download Images from Google Drive")
        st.markdown(
            """
            To download images from Google Drive, please upload your Google Service Account 
            credentials JSON file and provide the Google Sheet ID containing the image URLs.
            """
        )
        credentials_path = st.file_uploader("Upload Google Service Account Credentials", type=["json"])
        sheet_id = st.text_input("Google Sheet ID")
        output_folder = "downloaded_images"

        if credentials_path and sheet_id:
            download_button = st.button("Download Images")

            if download_button:
                try:
                    downloaded_image_paths = download_images_from_drive(credentials_path, sheet_id, output_folder)
                    st.success(f"Images downloaded successfully to {output_folder}.")
                except Exception as e:
                    st.error(f"Error downloading images: {str(e)}")

        else:
            st.warning("Please upload Google Service Account Credentials and provide Google Sheet ID.")

if __name__ == "__main__":
    main()
