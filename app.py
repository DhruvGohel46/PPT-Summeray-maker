import os
from flask import Flask, request, send_file, render_template


from werkzeug.utils import secure_filename

from PyPDF2 import PdfReader
import docx
from pptx import Presentation
from pptx.util import Inches
from transformers import BartTokenizer, BartForConditionalGeneration

# Initialize Flask app
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'output'

# Ensure the directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

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
def create_ppt(summary, output_path):
    prs = Presentation()
    slide_layout = prs.slide_layouts[1]  # Title and Content layout
    slide = prs.slides.add_slide(slide_layout)
    
    # Set title and content
    title_shape = slide.shapes.title
    title_shape.text = "Summary"
    if len(slide.placeholders) > 1:
        content_shape = slide.placeholders[1]
        content_shape.text = summary
    else:
        left = top = Inches(1)
        width = height = Inches(8)
        textbox = slide.shapes.add_textbox(left, top, width, height)
        textbox.text = summary

    prs.save(output_path)

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

        # Determine file type
        ext = os.path.splitext(filename)[1].lower()
        if ext == '.pdf':
            text = extract_text_from_pdf(upload_path)
        elif ext == '.docx':
            text = extract_text_from_docx(upload_path)
        else:
            return "Unsupported file type. Please upload a PDF or DOCX file.", 400

        summary = summarize_text(text)
        ppt_path = os.path.join(app.config['OUTPUT_FOLDER'], 'summary_presentation.pptx')
        create_ppt(summary, ppt_path)
        
        return send_file(ppt_path, as_attachment=True)
    
    return render_template('index.html')  # Update this path if necessary


if __name__ == '__main__':
    app.run(host='192.168.137.1', debug=True)
