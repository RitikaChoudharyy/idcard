import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io
import gspread

# Importing required libraries
import os
import base64
import pandas as pd
import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import textwrap
from fpdf import FPDF
from st_aggrid import AgGrid
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch, mm

# Function to preprocess image (convert to RGB)
def preprocess_image(image_path):
    try:
        input_image = Image.open(image_path)
        final_image = input_image.convert("RGB")
        return final_image
    except Exception as e:
        st.error(f"Error opening image at image_path: {str(e)}")
        return None

# Function to generate card
def generate_card(data, template_path, image_folder, qr_folder, drive_service):
    pic_id = str(data.get('ID', ''))
    if not pic_id:
        st.warning(f"Skipping record with missing ID: {data}")
        return None
    
    pic_path = os.path.join(image_folder, f"{pic_id}.jpg")
    if not os.path.exists(pic_path):
        st.info(f"Image not found locally for ID: {pic_id}. Attempting to download from Google Drive...")
        image_file_id = data.get('Google Drive File ID', '')  # Adjust column name as per your CSV
        if not image_file_id:
            st.error(f"No Google Drive File ID found for ID: {pic_id}. Cannot download image.")
            return None
        
        if download_image_from_drive(image_file_id, pic_path, drive_service):
            st.success(f"Image downloaded successfully for ID: {pic_id}")
        else:
            st.error(f"Failed to download image for ID: {pic_id}.")
            return None
    
    qr_path = os.path.join(qr_folder, f"{pic_id}.png")
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

# Function to download image from Google Drive
def download_image_from_drive(file_id, destination_path, drive_service):
    try:
        request = drive_service.files().get_media(fileId=file_id)
        fh = open(destination_path, 'wb')
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            print(f"Download {int(status.progress() * 100)}%.")
        fh.close()
        return True
    except Exception as e:
        st.error(f"Error downloading image from Google Drive: {str(e)}")
        return False

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

# Function to fetch images and generate cards
def fetch_images_and_generate_cards(csv_data, template_path, output_folder, qr_folder, credentials_path, drive_folder_id):
    try:
        # Authenticate with Google Drive API
        drive_service = authenticate_google_drive(credentials_path)
        if not drive_service:
            st.error("Failed to authenticate with Google Drive API.")
            return None

        generated_cards = []
        for _, data in csv_data.iterrows():
            generated_card = generate_card(data, template_path, output_folder, qr_folder, drive_service)
            if generated_card:
                generated_cards.append(generated_card)
            else:
                st.warning(f"Failed to generate card for ID: {data['ID']}")

        return generated_cards

    except Exception as e:
        st.error(f"Error fetching images and generating cards: {str(e)}")
        return None

# Function to generate PDF from generated cards
def generate_pdf(data, template_path, image_folder, qr_folder, output_pdf_path, drive_service):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    for _, data in data.iterrows():
        generated_card = generate_card(data, template_path, image_folder, qr_folder, drive_service)
        if generated_card:
            pdf.add_page()
            pdf.image(generated_card, x=10, y=10, w=185, h=300)
    pdf.output(output_pdf_path)
    st.success(f"PDF generated successfully: {output_pdf_path}")

# Function to authenticate with Google Drive API
def authenticate_google_drive(credentials_path):
    scopes = ['https://www.googleapis.com/auth/drive']
    try:
        credentials = service_account.Credentials.from_service_account_file(credentials_path, scopes=scopes)
        drive_service = build('drive', 'v3', credentials=credentials)
        return drive_service
    except Exception as e:
        st.error(f"Error authenticating with Google Drive API: {str(e)}")
        return None

# Function to create PDF from generated images
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

        x_positions = [spacing_x + (image_width + spacing_x) * i for i in range(grid_width)]
        y_positions = [spacing_y + (image_height + spacing_y) * i for i in range(grid_height)]

        # Iterate through the images and place them on the PDF
        for idx, image in enumerate(images):
            x = x_positions[idx % grid_width]
            y = letter[1] - y_positions[idx // grid_width] - image_height
            c.drawImage(image, x, y, width=image_width, height=image_height, preserveAspectRatio=True, anchor='c')

            if (idx + 1) % (grid_width * grid_height) == 0 and idx != 0:
                c.showPage()

        c.save()
        st.success(f"PDF file saved successfully: {pdf_path}")
    except Exception as e:
        st.error(f"Error creating PDF file: {str(e)}")

# Function to fetch data from Google Sheet
def fetch_data_from_google_sheet(credentials_path, sheet_name):
    try:
        scopes = ['https://www.googleapis.com/auth/spreadsheets']
        credentials = service_account.Credentials.from_service_account_file(credentials_path, scopes=scopes)
        gc = gspread.authorize(credentials)
        sheet = gc.open(sheet_name).sheet1  # Open the specified sheet
        
        # Load all values from the sheet
        data = sheet.get_all_values()
        
        # Convert to DataFrame
        df = pd.DataFrame(data[1:], columns=data[0])
        
        return df
    except Exception as e:
        st.error(f"Error fetching data from Google Sheet: {str(e)}")
        return None

# Main function to execute the Streamlit app
def main():
    st.title("ID Card Generation App")
    
    st.sidebar.header("Settings")
    sheet_name = st.sidebar.text_input("Google Sheet Name", "Sheet1")
    credentials_path = st.sidebar.file_uploader("Upload Google Service Account JSON")
    template_path = st.sidebar.file_uploader("Upload Template Image", type=["jpg", "jpeg", "png"])
    output_folder = st.sidebar.text_input("Output Image Folder Path", "./output_images")
    qr_folder = st.sidebar.text_input("QR Codes Folder Path", "./qr_codes")
    pdf_output_path = st.sidebar.text_input("Output PDF Path", "./output.pdf")
    drive_folder_id = st.sidebar.text_input("Google Drive Folder ID")
    
    if st.sidebar.button("Generate ID Cards"):
        # Check for required inputs
        if not all([sheet_name, credentials_path, template_path, output_folder, qr_folder, pdf_output_path, drive_folder_id]):
            st.warning("Please fill all the fields and upload necessary files.")
            return
        
        # Fetch data from Google Sheet
        csv_data = fetch_data_from_google_sheet(credentials_path, sheet_name)
        if csv_data is None:
            st.error("Failed to fetch data from Google Sheet.")
            return
        
        # Generate QR codes and save to folder
        generate_qr_codes(csv_data, qr_folder)
        
        # Generate ID cards and save to folder
        generated_cards = fetch_images_and_generate_cards(csv_data, template_path, output_folder, qr_folder, credentials_path, drive_folder_id)
        
        # Generate PDF from generated images
        if generated_cards:
            create_pdf(generated_cards, pdf_output_path)

if __name__ == "__main__":
    main()
