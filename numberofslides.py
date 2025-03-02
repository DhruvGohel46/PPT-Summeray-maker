def add_multiple_slides(prs, summary_text, num_slides, font_name="Calibri"):
    """
    Adds a specified number of slides to the presentation.
    
    Each slide uses the Title and Content layout (index 1) with:
      - A title indicating the slide number.
      - The summary text as the slide content.
      - Text formatted with the selected font.
    
    Args:
        prs (Presentation): An existing python-pptx Presentation object.
        summary_text (str): The summary text to include on each slide.
        num_slides (int): The number of slides to add.
        font_name (str): The name of the font to apply (default "Calibri").
    """
    for i in range(num_slides):
        slide_layout = prs.slide_layouts[1]  # Title and Content layout.
        slide = prs.slides.add_slide(slide_layout)
        # Set slide title (e.g. "Slide 1", "Slide 2", ...)
        slide.shapes.title.text = f"Slide {i+1}"
        # Set slide content to the summary text.
        slide.placeholders[1].text = summary_text

        # Apply the chosen font to the title
        for paragraph in slide.shapes.title.text_frame.paragraphs:
            for run in paragraph.runs:
                run.font.name = font_name
        # Apply the chosen font to the content text
        for paragraph in slide.placeholders[1].text_frame.paragraphs:
            for run in paragraph.runs:
                run.font.name = font_name
#add this to python ppt_summary_maker.py