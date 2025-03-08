import os
import io
import logging
from flask import Flask, request, send_file, render_template, redirect, url_for, flash, jsonify, session
from werkzeug.utils import secure_filename
from PyPDF2 import PdfReader

import docx
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
import google.generativeai as genai

# Initialize Flask app
app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app.secret_key = 'your_secret_key'  # Replace with a strong secret key
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'output'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure the directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# List of target audience options
TARGET_AUDIENCE_OPTIONS = {
    'students': "Designed for Students: Engaging and Informative",
    'professionals': "Targeting Professionals: Clear, Concise, Impactful",
    'researchers': "For Researchers: In-depth Analysis and Findings",
    'entrepreneurs': "For Entrepreneurs: Innovative and Future-Focused",
    'general': "General Audience: Broad Overview"
}

# List of font options
FONT_OPTIONS = {
    # Default options (shown first)
    'default': [
        'Calibri', 'Arial', 'Times New Roman', 'Verdana', 
        'Tahoma', 'Georgia', 'Segoe UI', 'Cambria',
        'Century Gothic', 'Garamond'
    ],
    # Additional options (shown when "More options" is clicked)
    'more': [
        'Palatino Linotype', 'Book Antiqua', 'Trebuchet MS', 'Courier New',
        'Franklin Gothic Medium', 'Lucida Sans', 'Constantia', 'Comic Sans MS',
        'Candara', 'MS Sans Serif', 'Arial Black', 'Impact', 'Rockwell',
        'Bookman Old Style', 'Copperplate Gothic', 'Bahnschrift', 'Consolas',
        'Lucida Console', 'Baskerville Old Face', 'Bookshelf Symbol 7'
    ]
}

# Function to extract text from a PDF
def extract_text_from_pdf(pdf_path):
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text
    except Exception as e:
        logger.error(f"Failed to read PDF file: {str(e)}")
        logger.info("Request method: %s", request.method)
        logger.info("Request data: %s", request.form)

        return None

# Function to extract text from a DOCX
def extract_text_from_docx(docx_path):
    try:
        doc = docx.Document(docx_path)
        text = ""
        for para in doc.paragraphs:
            text += para.text + "\n"
        return text
    except Exception as e:
        logger.error(f"Failed to read DOCX file: {str(e)}")
        logger.info("Request method: %s", request.method)
        logger.info("Request data: %s", request.form)

        return None

# Summarize text using Google's Gemini model
def summarize_text(text, goal=None, audience=None, num_slides=None):
    try:
        # Get API key from environment variable
        api_key = os.environ.get('GOOGLE_API_KEY')
        if not api_key:
            logger.warning("No API key found in environment. Using fallback method.")
            # Note: In production, remove this hardcoded key and use only environment variables
            api_key = "AIzaSyATGHln42rKoibkMUByJp3cPYpO5322zUs"
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")

        # Ensure goal and audience are not None or empty
        goal_text = goal if goal else "General goal"
        audience_text = audience if audience else "General audience"
        slides_text = f" Please create content for {num_slides} slides." if num_slides else ""

        prompt = f"Please provide a concise summary of the following text. " \
                f"The goal of this presentation is: {goal_text}. " \
                f"The target audience is: {audience_text}.{slides_text} " \
                f"Text:\n\n{text}"
        
        response = model.generate_content(prompt)
        return response.text if response and response.text else "Summary not generated."
    except Exception as e:
        logger.error(f"Error during summarization: {str(e)}")
        logger.info("Request method: %s", request.method)
        logger.info("Request data: %s", request.form)

        return f"Error during summarization: {str(e)}"

# Estimate number of slides needed for a summary
def estimate_slides(summary):
    # Simple estimation: about 30-40 words per slide
    words = summary.split()
    return max(1, len(words) // 35)

# Create a PowerPoint file with the summary
def create_ppt(summary, output_path, title=None, goal=None, audience=None, font_name='Calibri', num_slides=None):
    prs = Presentation()
    
    # Title slide
    title_slide = prs.slides.add_slide(prs.slide_layouts[0])
    title_placeholder = title_slide.shapes.title
    subtitle_placeholder = title_slide.placeholders[1]
    
    # Set title
    title_text = title if title else "Presentation Summary"
    title_placeholder.text = title_text
    
    # Set subtitle based on goal and audience
    subtitle_text = ""
    if goal:
        subtitle_text += f"Goal: {goal}"
    if audience:
        if subtitle_text:
            subtitle_text += " | "
        subtitle_text += f"Audience: {audience}"
    
    subtitle_placeholder.text = subtitle_text if subtitle_text else "Generated Presentation"
    
    # Apply font to title slide
    for shape in title_slide.shapes:
        if hasattr(shape, "text_frame"):
            for paragraph in shape.text_frame.paragraphs:
                for run in paragraph.runs:
                    run.font.name = font_name
    
    # If specific number of slides requested, adjust content accordingly
    if num_slides and num_slides > 0:
        # Add content slides based on requested number
        add_content_slides(prs, summary, num_slides, font_name)
    else:
        # Add content slides based on content length
        add_multiple_slides(prs, summary, font_name)
    
    try:
        prs.save(output_path)
        logger.info(f"PowerPoint saved to {output_path}.")
        return True
    except Exception as e:
        logger.error(f"Error saving PowerPoint: {str(e)}")
        return False

def add_content_slides(prs, summary, num_slides, font_name='Calibri'):
    """Add a specific number of slides distributing the content evenly"""
    # Remove title slide from count since we already created it
    content_slides = max(1, num_slides - 1)
    
    # Split the summary text into roughly equal parts
    words = summary.split()
    if not words:
        # If no content, add a single empty slide
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        slide.shapes.title.text = "Summary"
        slide.placeholders[1].text = "No content available."
        return
    
    words_per_slide = max(1, len(words) // content_slides)
    
    # Create the content slides
    for i in range(content_slides):
        start_idx = i * words_per_slide
        end_idx = min(start_idx + words_per_slide, len(words))
        
        # If this is the last slide, include all remaining words
        if i == content_slides - 1:
            end_idx = len(words)
        
        slide_content = ' '.join(words[start_idx:end_idx])
        
        # Add the slide
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        slide.shapes.title.text = f"Part {i+1}"
        content_shape = slide.placeholders[1]
        content_shape.text = slide_content
        
        # Apply font
        for shape in slide.shapes:
            if hasattr(shape, "text_frame"):
                for paragraph in shape.text_frame.paragraphs:
                    for run in paragraph.runs:
                        run.font.name = font_name

def add_multiple_slides(prs, summary, font_name='Calibri'):
    """Add multiple slides based on content length"""
    # Split the summary into paragraphs
    paragraphs = summary.split('\n')
    
    # Group paragraphs into slides (roughly 2-3 paragraphs per slide)
    slides_content = []
    current_slide = []
    current_length = 0
    
    for para in paragraphs:
        if para.strip():  # Skip empty paragraphs
            # If current slide is getting too long, start a new one
            if current_length > 300 or len(current_slide) >= 3:
                slides_content.append('\n\n'.join(current_slide))
                current_slide = [para]
                current_length = len(para)
            else:
                current_slide.append(para)
                current_length += len(para)
    
    # Add the last slide if not empty
    if current_slide:
        slides_content.append('\n\n'.join(current_slide))
    
    # If no content was processed, add a single slide
    if not slides_content:
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        slide.shapes.title.text = "Summary"
        slide.placeholders[1].text = "No content available."
        return
    
    # Create slides with the grouped content
    for i, content in enumerate(slides_content):
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        slide.shapes.title.text = f"Part {i+1}"
        content_shape = slide.placeholders[1]
        content_shape.text = content
        
        # Apply font
        for shape in slide.shapes:
            if hasattr(shape, "text_frame"):
                for paragraph in shape.text_frame.paragraphs:
                    for run in paragraph.runs:
                        run.font.name = font_name

@app.route('/', methods=['GET'])
def index():
    """Render the initial page with file type selection"""
    return render_template('index.html')

@app.route('/setup', methods=['POST'])
def setup():
    """Handle the file type selection and render the form"""
    file_type = request.form.get('file_type')
    if file_type not in ['pdf', 'docx']:
        flash("Please select a valid file type.")
        return redirect(url_for('index'))
    
    session['file_type'] = file_type
    return render_template(
        'setup_form.html', 
        file_type=file_type,
        audience_options=TARGET_AUDIENCE_OPTIONS,
        font_options=FONT_OPTIONS
    )

@app.route('/process', methods=['POST'])
def process():
    """Process the uploaded file and form data"""
    # Get form data
    title = request.form.get('title', 'Presentation')
    audience = request.form.get('audience', 'general')
    goal = request.form.get('goal', '')
    font_name = request.form.get('font', 'Calibri')
    file_type = session.get('file_type', 'pdf')
    
    # Check if file was uploaded
    if 'file' not in request.files or request.files['file'].filename == '':
        flash("Please upload a file.")
        return redirect(url_for('setup'))
    
    file = request.files['file']
    filename = secure_filename(file.filename)
    
    # Check file extension
    ext = os.path.splitext(filename)[1].lower()
    expected_ext = '.pdf' if file_type == 'pdf' else '.docx'
    
    if ext != expected_ext:
        flash(f"Please upload a {file_type.upper()} file. You selected {file_type} but uploaded a file with extension {ext}.")
        return redirect(url_for('setup'))
    
    # Save the file
    upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(upload_path)
    
    # Extract text from the file
    if file_type == 'pdf':
        text = extract_text_from_pdf(upload_path)
    else:  # docx
        text = extract_text_from_docx(upload_path)
    
    if not text:
        flash(f"Error: Could not extract text from the {file_type.upper()} file.")
        return redirect(url_for('setup'))
    
    # Summarize the text
    summary = summarize_text(text, goal=goal, audience=audience)
    
    # Estimate number of slides
    estimated_slides = estimate_slides(summary)
    
    # Save data in session for later use
    session['summary'] = summary
    session['title'] = title
    session['audience'] = audience
    session['goal'] = goal
    session['font_name'] = font_name
    session['estimated_slides'] = estimated_slides
    
    # Show confirmation page
    return render_template('confirm.html', estimated_slides=estimated_slides)

@app.route('/confirm', methods=['POST'])
def confirm():
    """Handle slide count confirmation and generate the final PPT"""
    response = request.form.get('response', '').lower()
    
    # Get saved data from session
    summary = session.get('summary', '')
    title = session.get('title', 'Presentation')
    audience = session.get('audience', 'general')
    goal = session.get('goal', '')
    font_name = session.get('font_name', 'Calibri')
    estimated_slides = session.get('estimated_slides', 5)
    
    if not summary:
        flash("Session expired. Please upload your file again.")
        return redirect(url_for('index'))
    
    num_slides = None  # Default to auto-detect
    
    if response == 'no':
        # User wants custom slide count
        custom_slides = request.form.get('custom_slides', '')
        try:
            num_slides = int(custom_slides)
            if num_slides <= 0:
                raise ValueError("Slide count must be positive")
        except ValueError:
            flash("Please enter a valid number of slides.")
            return render_template('confirm.html', estimated_slides=estimated_slides)
    
    logger.info("Generating the PowerPoint presentation.")
    # Generate the PPT

    output_filename = f"{secure_filename(title)}.pptx"
    output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
    
    success = create_ppt(
        summary, 
        output_path, 
        title=title, 
        goal=goal, 
        audience=audience, 
        font_name=font_name,
        num_slides=num_slides
    )
    
    if not success:
        logger.error("Failed to generate the PowerPoint presentation.")

        flash("Error generating the presentation. Please try again.")
        return redirect(url_for('index'))
    
    # Check if the output file exists before sending
    if not os.path.exists(output_path):
        flash("Error: The PowerPoint file was not generated.")
        return redirect(url_for('index'))

    # Clear session data only after successful download
    session.clear()  

    
    # Send the file
    logger.info(f"Sending the PowerPoint file: {output_filename}")
    return send_file(

        output_path,
        as_attachment=True,
        download_name=output_filename,
        mimetype="application/vnd.openxmlformats-officedocument.presentationml.presentation"
    )

@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle file too large error"""
    flash("The file you uploaded is too large. Please upload a file smaller than 16MB.")
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='127.0.0.1', debug=True)
