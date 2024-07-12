import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import psycopg2
import mysql.connector
from datetime import datetime
import base64
from PIL import Image, ImageDraw, ImageFont
import io
import textwrap
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch, mm
import fitz
import os
import logging

# Database configurations
postgres_config = {
    'dbname': 'internship_data',
    'user': 'root',
    'password': 'Ritika@123',
    'host': 'localhost',
    'port': 5432  # Default PostgreSQL port is 5432, not 3306
}

mysql_config = {
    'host': 'localhost',
    'database': 'internship_details',
    'user': 'root',
    'password': 'Ritika@123'
}

# Password protection function
def authenticate():
    password = st.text_input("Enter password:", type="password")
    return password

# Check password function
def check_password(password):
    return password == "Ritika"

# Authenticate
password = authenticate()
if check_password(password):
    st.sidebar.success("Authentication successful!")
else:
    st.sidebar.error("Authentication failed. Please try again.")
    st.stop()

# Function to execute PostgreSQL queries
def execute_postgres_query(query):
    conn = psycopg2.connect(**postgres_config)
    try:
        with conn.cursor() as cursor:
            cursor.execute(query)
            if cursor.description:
                result = cursor.fetchall()
                result_df = pd.DataFrame(result, columns=[col[0] for col in cursor.description])
                st.write(result_df)
            conn.commit()
    except Exception as e:
        st.error(f"Error executing query: {str(e)}")
        logging.error(f"Error executing query: {str(e)}")
    finally:
        conn.close()

# Function to execute MySQL queries
def execute_mysql_query(query):
    try:
        connection = mysql.connector.connect(**mysql_config)
        if connection.is_connected():
            cursor = connection.cursor()
            cursor.execute(query)
            records = cursor.fetchall()
            st.write("Query executed successfully!")
            st.write("Local Address:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            if records:
                st.write("Query Result:")
                df = pd.DataFrame(records, columns=[i[0] for i in cursor.description])
                st.write(df)

                fig = go.Figure()
                for col in df.columns:
                    if df[col].dtype == 'int64' or df[col].dtype == 'float64':
                        fig.add_trace(go.Scatter(x=df.index, y=df[col], mode='lines+markers', name=col))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.write("No records found.")
    except Exception as e:
        st.error(f"Error: {e}")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

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

# Function to create PDF from images
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

# Function to display PDF
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

# Function to center-align text
def center_align_text_wrapper(text, width):
    lines = textwrap.wrap(text, width=width)
    return "\n".join([line.center(width) for line in lines])

# Dummy function for division head lookup
def get_head_by_division(division):
    head_mapping = {
        "IT": "John Doe",
        "HR": "Jane Smith",
        "Finance": "Richard Roe",
        "Marketing": "Mary Major"
    }
    return head_mapping.get(division, "Unknown")

# Function to process and generate ID cards
def process_data_and_generate_cards(data_df, template_path, image_folder, qr_folder):
    all_images = []
    for idx, row in data_df.iterrows():
        id_card = generate_card(row, template_path, image_folder, qr_folder)
        if id_card:
            image_path = f"{image_folder}/{row['ID']}_processed.jpg"
            id_card.save(image_path)
            all_images.append(image_path)
    
    if all_images:
        pdf_path = "generated_id_cards.pdf"
        pdf_path = create_pdf(all_images, pdf_path)
        if pdf_path:
            st.success("ID Cards generated and PDF created successfully.")
            display_pdf(pdf_path)
        else:
            st.error("Error creating the PDF.")
    else:
        st.warning("No images to process into PDF.")

# Function for string formatting
def remove_spaces(text):
    return text.replace(' ', '')

def remove_special_chars(text):
    special_chars = ['.', ',', '!', '@', '#', '$', '%', '^', '&', '*', '(', ')', '-', '_', '=', '+', '{', '}', '[', ']', '|', '\\', ':', ';', '"', "'", '<', '>', '?', '/', '`', '~']
    for char in special_chars:
        text = text.replace(char, '')
    return text

def remove_tabs(text):
    return text.replace('\t', '')

def process_text(text):
    text = remove_spaces(text)
    text = remove_special_chars(text)
    text = remove_tabs(text)
    return text

# Main application logic
def main():
    st.title("Database Query Executor and ID Card Generator")
    st.sidebar.header("Database Query")

    database_type = st.sidebar.selectbox("Select Database Type", ("PostgreSQL", "MySQL"))

    if database_type == "PostgreSQL":
        query = st.sidebar.text_area("Enter your PostgreSQL query")
        if st.sidebar.button("Execute PostgreSQL Query"):
            execute_postgres_query(query)
    else:
        query = st.sidebar.text_area("Enter your MySQL query")
        if st.sidebar.button("Execute MySQL Query"):
            execute_mysql_query(query)
    
    st.sidebar.header("ID Card Generator")
    
    template_path = st.sidebar.text_input("Template Path")
    image_folder = st.sidebar.text_input("Image Folder Path")
    qr_folder = st.sidebar.text_input("QR Folder Path")
    
    if st.sidebar.button("Generate ID Cards"):
        try:
            data = {
                "ID": [1, 2, 3],
                "Name": ["Alice", "Bob", "Charlie"],
                "Division/Section": ["IT", "HR", "Finance"],
                "Internship Start Date": ["2024-07-01", "2024-07-02", "2024-07-03"],
                "Internship End Date": ["2024-12-01", "2024-12-02", "2024-12-03"],
                "Mobile": ["1234567890", "2345678901", "3456789012"],
                "University": ["Uni A", "Uni B", "Uni C"]
            }
            data_df = pd.DataFrame(data)
            process_data_and_generate_cards(data_df, template_path, image_folder, qr_folder)
        except Exception as e:
            st.error(f"Error generating ID cards: {str(e)}")

# Entry point for the application
if __name__ == "__main__":
    main()
