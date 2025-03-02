import os
import io
from flask import Flask, request, send_file, render_template, redirect, url_for, flash
from werkzeug.utils import secure_filename
from PyPDF2 import PdfReader
import docx
from pptx import Presentation
from pptx.util import Inches
from transformers import BartTokenizer, BartForConditionalGeneration
from tools.templates import get_available_templates

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a strong secret key
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'output'

# Ensure the directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# List of target audience options for reference
TARGET_AUDIENCE_OPTIONS = {
    'students': "Designed for Students: Engaging and Informative",
    'professionals': "Targeting Professionals: Clear, Concise, Impactful",
    'researchers': "For Researchers: In-depth Analysis and Findings",
    'entrepreneurs': "For Entrepreneurs: Innovative and Future-Focused",
    'general': "General Audience: Broad Overview"
}

# Function to extract text from a PDF
def extract_text_from_pdf(pdf_path):
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text

# Function to extract text from a DOCX
def extract_text_from_docx(docx_path):
    doc = docx.Document(docx_path)
    text = ""
    for para in doc.paragraphs:
        text += para.text + "\n"
    return text

# Summarize text using facebook/bart-large-cnn
def summarize_text(text):
    tokenizer = BartTokenizer.from_pretrained("facebook/bart-large-cnn")
    model = BartForConditionalGeneration.from_pretrained("facebook/bart-large-cnn")
    inputs = tokenizer(text, return_tensors="pt", max_length=1024, truncation=True)
    summary_ids = model.generate(
        inputs.input_ids,
        num_beams=4,
        max_length=150,
        min_length=50,
        early_stopping=True
    )
    summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
    return summary

# Create a PowerPoint file with the summary
def create_ppt(summary, output_path, goal=None, audience=None):

    prs = Presentation()
    slide_layout = prs.slide_layouts[1]  # Title and Content layout
    slide = prs.slides.add_slide(slide_layout)
    
    # Set title and content
    title_shape = slide.shapes.title
    title_shape.text = "Summary"
    if goal:
        title_shape.text += f" - Goal: {goal}"  # Include the goal in the title
    if len(slide.placeholders) > 1:
        content_shape = slide.placeholders[1]
        content_shape.text = summary
    else:
        left = top = Inches(1)
        width = height = Inches(8)
        textbox = slide.shapes.add_textbox(left, top, width, height)
        textbox.text = summary

    # Customize the presentation based on the audience
    if audience:
        if 'students' in audience:
            # Add specific slides or content for students
            pass  # Implement specific logic for students
        elif 'professionals' in audience:
            # Add specific slides or content for professionals
            pass  # Implement specific logic for professionals
        elif 'researchers' in audience:
            # Add specific slides or content for researchers
            pass  # Implement specific logic for researchers
        elif 'entrepreneurs' in audience:
            # Add specific slides or content for entrepreneurs
            pass  # Implement specific logic for entrepreneurs
        elif 'general' in audience:
            # Add specific slides or content for general audience
            pass  # Implement specific logic for general audience

    prs.save(output_path)


# Create a PowerPoint presentation customized based on the target audience
def create_ppt_with_audience(audience_list: list) -> io.BytesIO:
    prs = Presentation()
    slide_layout = prs.slide_layouts[0]  # Title slide layout
    slide = prs.slides.add_slide(slide_layout)
    
    title = slide.shapes.title
    subtitle = slide.placeholders[1]
    
    title.text = "Presentation"
    
    # Determine a default subtitle
    custom_subtitle = "Customized Presentation"
    if 'students' in audience_list:
        custom_subtitle = TARGET_AUDIENCE_OPTIONS['students']
        slide2 = prs.slides.add_slide(prs.slide_layouts[1])
        slide2.shapes.title.text = "Study Tips"
        slide2.placeholders[1].text = "Effective study habits and time management tips."
    elif 'professionals' in audience_list:
        custom_subtitle = TARGET_AUDIENCE_OPTIONS['professionals']
        slide2 = prs.slides.add_slide(prs.slide_layouts[1])
        slide2.shapes.title.text = "Professional Insights"
        slide2.placeholders[1].text = "Focus on productivity and career growth strategies."
    elif 'researchers' in audience_list:
        custom_subtitle = TARGET_AUDIENCE_OPTIONS['researchers']
        slide2 = prs.slides.add_slide(prs.slide_layouts[1])
        slide2.shapes.title.text = "Research Findings"
        slide2.placeholders[1].text = "Latest data and detailed analysis."
    elif 'entrepreneurs' in audience_list:
        custom_subtitle = TARGET_AUDIENCE_OPTIONS['entrepreneurs']
        slide2 = prs.slides.add_slide(prs.slide_layouts[1])
        slide2.shapes.title.text = "Entrepreneurial Strategies"
        slide2.placeholders[1].text = "Innovative ideas and market insights."
    elif 'general' in audience_list:
        custom_subtitle = TARGET_AUDIENCE_OPTIONS['general']
    
    subtitle.text = f"Target Audience: {custom_subtitle}"
    
    # Save presentation to a BytesIO stream
    ppt_stream = io.BytesIO()
    prs.save(ppt_stream)
    ppt_stream.seek(0)
    return ppt_stream

@app.route('/target-audience', methods=['GET', 'POST'])
def target_audience():
    if request.method == 'POST':
        selected_audience = request.form.getlist('audience')
        if not selected_audience:
            flash("Please select at least one target audience.")
            return redirect(url_for('target_audience'))
        
        ppt_file = create_ppt_with_audience(selected_audience)
        return send_file(
            ppt_file,
            as_attachment=True,
            attachment_filename="presentation.pptx",
            mimetype="application/vnd.openxmlformats-officedocument.presentationml.presentation"
        )
    
    return render_template('target_audience.html', options=TARGET_AUDIENCE_OPTIONS)

# Route for home page
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'datafile' not in request.files:
            return "No file part", 400
        file = request.files['datafile']
        if file.filename == '':
            return "No selected file", 400
        
        filename = secure_filename(file.filename)
        upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(upload_path)

        presentation_goal = request.form.get('goal')  # Retrieve the goal input from the form

        # Determine file type        
        ext = os.path.splitext(filename)[1].lower()
        if ext == '.pdf':
            text = extract_text_from_pdf(upload_path)
        elif ext == '.docx':
            text = extract_text_from_docx(upload_path)
        else:
            return "Unsupported file type. Please upload a PDF or DOCX file.", 400

        if text:
            summary = summarize_text(text)
        else:
            return "Error processing the file.", 400

        ppt_path = os.path.join(app.config['OUTPUT_FOLDER'], 'summary_presentation.pptx')        
        create_ppt(summary, ppt_path, goal=presentation_goal, audience=request.form.getlist('audience'))  # Pass the presentation goal and audience to create_ppt

        
        return send_file(ppt_path, as_attachment=True)  # Send the generated PPT back to the user

    templates = get_available_templates()
    return render_template('index.html', templates=templates)  # Pass templates to the index.html

if __name__ == '__main__':
    app.run(host='127.0.0.1', debug=True)
