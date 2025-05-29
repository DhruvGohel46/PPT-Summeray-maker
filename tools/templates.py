import os
def get_available_templates(directory='PPT templates'):
    """Return a list of available template filenames in the specified directory."""
    return [f for f in os.listdir(directory) if f.endswith(('.pptx', '.ppt'))]
