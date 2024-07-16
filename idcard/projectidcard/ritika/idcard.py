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
import mysql.connector
import logging
from mysql.connector import Error

# Configure logging to capture errors
logging.basicConfig(filename='app.log', level=logging.ERROR, format='%(asctime)s - %(message)s')

# Function to create MySQL connection
def create_connection():
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="Ritika@12",
            database="id_card_system"
        )
        if connection.is_connected():
            st.write("Connected to MySQL database")
        return connection
    except Error as e:
        st.error(f"Error: {e}")
        return None

# Function to close MySQL connection
def close_connection(connection):
    if connection.is_connected():
        connection.close()
        st.write("MySQL connection is closed")

# Function to execute a MySQL query
def execute_mysql_query(query):
    connection = create_connection()
    if connection is not None:
        try:
            cursor = connection.cursor()
            cursor.execute(query)
            connection.commit()
            st.write("Query executed successfully")
        except Error as e:
            st.error(f"Error executing query: {e}")
        finally:
            cursor.close()
            close_connection(connection)

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


# Function to create PDF of generated ID cards
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


# Function to display PDF download link
def display_pdf(pdf_path):
    try:
        with open(pdf_path, "rb") as f:
            base64_pdf = base64.b64encode(f.read()).decode('utf-8')
            pdf_display = f'<a href="data:application/pdf;base64,{base64_pdf}" download="generated_id_cards.pdf">Download PDF</a>'
            st.markdown(pdf_display, unsafe_allow_html=True)
    except FileNotFoundError:
        st.error(f"PDF file not found at path: {pdf_path}")


# Main function to run the Streamlit app
def main():
    st.title("Intern ID Card Generation System")

    menu = ["Home", "View Data", "Generate ID Cards"]
    choice = st.sidebar.selectbox("Menu", menu)

    # Connect to MySQL database
    connection = create_connection()

    if choice == "Home":
        st.subheader("Home")
        st.write("Welcome to the Intern ID Card Generation System!")

    elif choice == "View Data":
        st.subheader("View Data")
        
        query = "SELECT * FROM intern_details"
        df = execute_query(connection, query)
        
        if df is not None:
            AgGrid(df)

    elif choice == "Generate ID Cards":
        st.subheader("Generate ID Cards")
        st.write("Please select an intern ID from the dropdown list to generate their ID card:")

        # Fetch intern IDs from MySQL database
        query = "SELECT ID FROM intern_details"
        cursor = connection.cursor()
        cursor.execute(query)
        ids = [row[0] for row in cursor.fetchall()]
        cursor.close()

        selected_id = st.selectbox("Select Intern ID", ids)

        if st.button("Generate ID Card"):
            # Fetch intern details based on selected ID
            query = f"SELECT * FROM intern_details WHERE ID = {selected_id}"
            cursor = connection.cursor()
            cursor.execute(query)
            data = cursor.fetchone()
            cursor.close()

            # Generate ID card for selected intern
            template_path = "id_card_template.jpg"  # Update with your template path
            image_folder = "images"  # Update with your image folder path
            qr_folder = "qrcodes"  # Update with your QR code folder path

            card_image = generate_card(data, template_path, image_folder, qr_folder)

            if card_image is not None:
                st.image(card_image, caption=f"Generated ID Card for ID: {selected_id}", use_column_width=True)

                # Option to download individual card as PDF
                if st.button("Download as PDF"):
                    pdf_filename = f"id_card_{selected_id}.pdf"
                    card_image.save(pdf_filename)
                    st.markdown(get_pdf_download_link(pdf_filename), unsafe_allow_html=True)

    # Close MySQL connection
    close_connection(connection)


if __name__ == "__main__":
    main()
