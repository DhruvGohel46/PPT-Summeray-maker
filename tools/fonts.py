import requests

def get_trending_fonts() -> list:
    """
    Fetch trending fonts from the Google Fonts API sorted by popularity.
    Returns a list of top font family names.
    """
    API_KEY = ""  # Insert your Google Fonts API key here
    url = f"https://www.googleapis.com/webfonts/v1/webfonts?key={API_KEY}&sort=popularity"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        # Extract the top 10 fonts
        trending_fonts = [font["family"] for font in data.get("items", [])][:10]
        return trending_fonts
    except Exception as e:
        print("Error fetching trending fonts:", e)
        # Fallback list if API call fails
        return ["Roboto", "Open Sans", "Lato", "Montserrat", "Oswald", "Raleway"]

# Example Flask route to provide the list in a dropdown:
@app.route('/select-font', methods=['GET'])
def select_font():
    fonts = get_trending_fonts()
    return render_template('select_font.html', fonts=fonts)
