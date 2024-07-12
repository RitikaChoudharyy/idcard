import streamlit as st
import os
from PIL import Image, ImageDraw, ImageFont
import logging
import base64
import textwrap
import mysql.connector
import pandas as pd
from reportlab.lib.pagesizes import letter, inch
from reportlab.pdfgen import canvas

# MySQL connection details
mysql_config = {
    'host': 'localhost',
    'user': 'root',
    'port': 3306,
    'password': 'Ritika@123',
    'database': 'id_card_db'
}

def get_mysql_connection(config):
    return mysql.connector.connect(
        host=config['host'],
        user=config['user'],
        port=config['port'],
        password=config['password'],
        database=config['database']
    )

# Function to execute MySQL queries
def execute_mysql_query(query):
    try:
        connection = get_mysql_connection(mysql_config)
        cursor = connection.cursor()
        cursor.execute(query)
        if cursor.with_rows:
            result = cursor.fetchall()
            result_df = pd.DataFrame(result, columns=cursor.column_names)
            st.write(result_df)
        connection.commit()
    except Exception as e:
        st.error(f"Error executing query: {str(e)}")
        logging.error(f"Error executing query: {str(e)}")
    finally:
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

# Function to clean table and column names
def clean_name(name):
    return name.strip().lower().replace(' ', '_').replace('/', '_')

# Function to store CSV data into MySQL
def store_csv_to_mysql(csv_data, table_name):
    try:
        connection = get_mysql_connection(mysql_config)
        cursor = connection.cursor()

        # Clean column names
        csv_data.columns = [clean_name(col) for col in csv_data.columns]

        # Generate column names for the insert query
        columns = ', '.join(csv_data.columns)

        # Prepare placeholders for values in the insert query
        placeholders = ', '.join(['%s'] * len(csv_data.columns))

        # Create the insert query
        insert_query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"

        # Convert DataFrame rows to tuples to use with cursor.executemany
        values = [tuple(row) for row in csv_data.values]

        # Execute the insert query with multiple rows
        cursor.executemany(insert_query, values)
        connection.commit()

        st.success(f"CSV data stored to MySQL database successfully in table '{table_name}'.")

    except mysql.connector.Error as e:
        st.error(f"Error storing CSV data to MySQL: {str(e)}")
        logging.error(f"Error storing CSV data to MySQL: {str(e)}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()

# Function to generate download link for binary files
def get_binary_file_downloader_html(bin_file, file_label='File'):
    with open(bin_file, 'rb') as f:
        data = f.read()
    bin_str = base64.b64encode(data).decode()
    return f'<a href="data:application/octet-stream;base64,{bin_str}" download="{os.path.basename(bin_file)}">{file_label}</a>'

def main():
    st.title("Automatic ID Card Generation")

    # Update these paths according to your file locations
    template_path = "idcard/projectidcard/ritika/ST.png"
    image_folder = "idcard/projectidcard/ritika/downloaded_images"
    qr_folder = "idcard/projectidcard/ritika/ST_output_qr_codes"
    output_pdf_path_default = "C:\\Users\\Shree\\Downloads\\generated_id_cards.pdf"  # Default download path

    # Section for CSV management
    st.sidebar.header('Manage CSV')

    csv_files = st.sidebar.file_uploader("Upload or Update your CSV files", type=['csv'], accept_multiple_files=True, key='csv_uploader')

    if csv_files is not None:
        for csv_file in csv_files:
            try:
                csv_data = pd.read_csv(csv_file)
                table_name = os.path.splitext(os.path.basename(csv_file.name))[0]
                st.sidebar.success(f'CSV file {csv_file.name} successfully uploaded/updated.')
                store_csv_to_mysql(csv_data, table_name)  # Automatically store CSV data into MySQL
            except Exception as e:
                st.error(f"Error reading CSV file {csv_file.name}: {str(e)}")

    # Section for MySQL query execution
    st.sidebar.header('MySQL Query Execution')
    query = st.sidebar.text_area("Enter MySQL Query")
    
    if st.sidebar.button("Execute Query"):
        if query:
            execute_mysql_query(query)
        else:
            st.sidebar.error("Please enter a MySQL query.")

    # Section to generate ID cards
    st.subheader('Generate ID Cards')
    generate_mode = st.radio("Select ID card generation mode:", ('Individual ID', 'Comma-separated IDs', 'All Students'))

    if generate_mode == 'Individual ID':
        id_input = st.text_input('Enter the ID:')
        if st.button('Generate ID Card'):
            if not id_input.isdigit():
                st.warning('Invalid input. Please enter a valid numeric ID.')
            else:
                selected_data = csv_data[csv_data['ID'] == int(id_input)].iloc[0]
                generated_card = generate_card(selected_data, template_path, image_folder, qr_folder)
                if generated_card:
                    st.image(generated_card, caption=f"Generated ID Card for ID: {id_input}")

    elif generate_mode == 'Comma-separated IDs':
        ids_input = st.text_input('Enter comma-separated IDs:')
        if st.button('Generate ID Cards'):
            id_list = [int(id.strip()) for id in ids_input.split(',') if id.strip().isdigit()]
            generated_cards = []

            for id_input in id_list:
                selected_data = csv_data[csv_data['ID'] == id_input].iloc[0]
                generated_card = generate_card(selected_data, template_path, image_folder, qr_folder)
                if generated_card:
                    generated_cards.append(generated_card)

            if generated_cards:
                st.success(f"Generated {len(generated_cards)} ID cards.")
                for i, card in enumerate(generated_cards):
                    st.image(card, caption=f"Generated ID Card for ID: {id_list[i]}")

                # Create PDF of generated ID cards
                pdf_path = create_pdf(generated_cards, output_pdf_path_default)
                if pdf_path:
                    st.success(f"PDF created successfully.")
                    # Display download button for the PDF
                    st.markdown(get_binary_file_downloader_html(pdf_path, 'Download PDF'), unsafe_allow_html=True)
                else:
                    st.error("Failed to create PDF.")

    elif generate_mode == 'All Students':
        st.info("Generating ID cards for all students...")
        generated_cards = []

        for index, data in csv_data.iterrows():
            generated_card = generate_card(data, template_path, image_folder, qr_folder)
            if generated_card:
                generated_cards.append(generated_card)

        if generated_cards:
            st.success(f"Generated {len(generated_cards)} ID cards.")

            # Create PDF of generated ID cards
            pdf_path = create_pdf(generated_cards, output_pdf_path_default)
            if pdf_path:
                st.success(f"PDF created successfully.")
                # Display download button for the PDF
                st.markdown(get_binary_file_downloader_html(pdf_path, 'Download PDF'), unsafe_allow_html=True)
            else:
                st.error("Failed to create PDF.")

if __name__ == "__main__":
    main()
