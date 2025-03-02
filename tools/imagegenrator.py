import os
import requests
import logging

# Load your Unsplash Access Key from an environment variable
ACCESS_KEY = os.environ.get('UNSPLASH_ACCESS_KEY')
if not ACCESS_KEY:
    raise ValueError("Unsplash access key not set in environment variable 'UNSPLASH_ACCESS_KEY'")

def search_images(query: str, num: int = 5) -> list:
    """
    Search for images on Unsplash based on a query.

    Args:
        query (str): The search term.
        num (int): Number of images to retrieve (default is 5).

    Returns:
        list: A list of image URLs from Unsplash.
    """
    url = f"https://api.unsplash.com/search/photos"
    params = {
        "query": query,
        "per_page": num,
        "client_id": ACCESS_KEY
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()  # Raises an HTTPError for bad responses
    except requests.RequestException as e:
        logging.error(f"Error during Unsplash API request: {e}")
        return []
    
    try:
        data = response.json()
    except ValueError as e:
        logging.error(f"Error decoding JSON: {e}")
        return []
    
    image_urls = []
    for item in data.get('results', []):
        image_urls.append(item['urls']['regular'])
    
    return image_urls

if __name__ == "__main__":
    query = input("Enter your search query: ")
    images = search_images(query)
    print("Image URLs:")
    for img in images:
        print(img)
