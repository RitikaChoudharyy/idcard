import face_recognition
import numpy as np

def preprocess_image(image_path):
    try:
        input_image = Image.open(image_path)
        final_image = input_image.convert("RGB")
        return final_image
    except Exception as e:
        st.error(f"Error opening image at image_path: {str(e)}")
        return None

def detect_and_crop_face(image_path):
    try:
        image = face_recognition.load_image_file(image_path)
        face_locations = face_recognition.face_locations(image)

        if not face_locations:
            st.warning(f"No faces detected in image: {image_path}")
            return None

        # Assuming only one face is detected, crop the first one
        top, right, bottom, left = face_locations[0]
        face_image = image[top:bottom, left:right]
        face_image = Image.fromarray(face_image)

        # Resize the cropped face image to 144x149
        resized_face = face_image.resize((144, 149))

        return resized_face
    except Exception as e:
        st.error(f"Error detecting and cropping face: {str(e)}")
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

    # Preprocess the image and detect/crop face
    preprocessed_pic = preprocess_image(pic_path)
    if preprocessed_pic is None:
        return None

    try:
        # Detect and crop face
        cropped_face = detect_and_crop_face(pic_path)
        if cropped_face is None:
            return None

        # Load template and QR code
        template = Image.open(template_path)
        qr = Image.open(qr_path).resize((161, 159))

        # Resize and paste images onto the template
        preprocessed_pic_resized = preprocessed_pic.resize((144, 145))
        template.paste(preprocessed_pic_resized, (27, 113, 171, 258))
        template.paste(qr, (497, 109, 658, 268))

        draw = ImageDraw.Draw(template)

        # Add text and other details to the template
        try:
            font_path = "C:\\WINDOWS\\FONTS\\ARIAL.TTF"  # Update with your font path
            name_font = ImageFont.truetype(font_path, size=18)
        except IOError:
            name_font = ImageFont.load_default()

        # Adjust text wrapping and positioning as before
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

def main():
    # Streamlit setup
    st.title("Automatic ID Card Generation")

    # Update these paths according to your file locations
    template_path = "path/to/template.png"
    image_folder = "path/to/images"
    qr_folder = "path/to/qr_codes"
    output_pdf = "path/to/output_id_cards.pdf"

    uploaded_file = st.file_uploader("Choose a CSV file", type="csv")

    if uploaded_file is not None:
        try:
            data = pd.read_csv(uploaded_file)

            # Check if the essential columns are present
            essential_columns = ['ID', 'Name', 'Mobile', 'Division/Section', 'University', 'Internship Start Date', 'Internship End Date']
            for column in essential_columns:
                if column not in data.columns:
                    st.error(f"Essential column '{column}' is missing in the CSV file.")
                    return

            st.write("Data preview:", data.head())

            generate_cards = st.button("Generate ID Cards")

            if generate_cards:
                images = []
                for index, row in data.iterrows():
                    card = generate_card(row, template_path, image_folder, qr_folder)
                    if card:
                        images.append(card)

                if images:
                    pdf_path = create_pdf(images, output_pdf)
                    if pdf_path:
                        st.success(f"PDF created successfully and saved to: {pdf_path}")
                        display_pdf(pdf_path)
                    else:
                        st.error("Failed to create PDF.")
                else:
                    st.error("No valid cards generated. Please check the log for errors.")
        except pd.errors.EmptyDataError:
            st.error("The uploaded CSV file is empty.")
        except pd.errors.ParserError:
            st.error("Error parsing CSV file. Please check the file format.")
        except Exception as e:
            st.error(f"An unexpected error occurred: {str(e)}")

if __name__ == "__main__":
    main()
