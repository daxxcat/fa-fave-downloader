"""
Command-line interface for FA Fave Downloader.
"""
import argparse
import os
import re
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

# Import __version__ - handle both module and direct execution
try:
    from .__init__ import __version__
except ImportError:
    from fa_fave_downloader import __version__

# Constants
FA_URL = "https://www.furaffinity.net"

def get_favorite_image_urls_inner(gallery_favorites):
    """
    Inner function for getting favorite image urls from FA Favorites object.

    :param gallery_favorites: favorites object
    :return: a list of image urls
    """
    favourites_url = []
    for a in gallery_favorites.find_all('a'):
        if a.find('img'):
            href = a.get('href')
            if href:
                # Ensure full URL
                if href.startswith('/'):
                    href = FA_URL + href
                favourites_url.append(href)
    return favourites_url

def get_favorite_image_urls(username, cookies=None):
    """
    Retrieve the HTML page for the user's favorites and extract image URLs from the gallery-section.

    Args:
        username (str): The Fur Affinity username.
        cookies (dict, optional): Optional cookies to use for authenticated requests.

    Returns:
        list: List of image URLs found in the gallery-favorites section.
    """
    print(f"Retrieving favorite image URLs for user: {username} ...")
    url = f"{FA_URL}/favorites/{username}/"
    response = requests.get(url, cookies=cookies)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')
    gallery_favorites = soup.find('section', id='gallery-favorites')
    if not gallery_favorites:
        return []

    favourites_url = get_favorite_image_urls_inner(gallery_favorites)

    # Check for pagination
    next_page_url = get_next_page_url(f"{FA_URL}/favorites/{username}/", cookies=cookies)
    while next_page_url:
        response = requests.get(next_page_url, cookies=cookies)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        gallery_favorites = soup.find('section', id='gallery-favorites')
        if not gallery_favorites:
            break
        favourites_url += get_favorite_image_urls_inner(gallery_favorites)
        # Get next page
        next_page_url = get_next_page_url(next_page_url, cookies=cookies)

    print(f"Found {len(favourites_url)} favorite image URLs for user: {username}")
    return favourites_url


def get_next_page_url(url, cookies=None):
    """
    Check if there is a 'Next' button on the favorites page and return the URL to the next page if found.

    Args:
        url (str): The URL of the favorites page to check.
        cookies (dict, optional): Optional cookies to use for authenticated requests.

    Returns:
        str or None: The URL of the next page if a 'Next' button is found, otherwise None.
    """
    response = requests.get(url, cookies=cookies)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')

    # Look for a form containing a button with text 'Next' (case-insensitive)
    next_form = soup.find('form', method='get', action=lambda text: text and 'next' in text.lower())
    if next_form:
        href = next_form.get('action')
        if href:
            # Ensure full URL
            if href.startswith('/'):
                href = FA_URL + href
            return href

    return None


def sanitize_filename(name):
    """Sanitize filename by replacing invalid characters with underscores and consecutive spaces with a single dash."""
    # First replace invalid characters with underscores
    name = re.sub(r'[^\w\-_\. ]', '_', name)
    # Trim spaces where ' - ' is used
    name = re.sub(r' - ', '-', name)
    # Replace consecutive spaces with a single dash
    name = re.sub(r'\s+', '-', name)
    return name


def download_favorite(url, save_path, cookies=None):
    """
    Download the favourite image from the url section.

    Args:
        url (str): The url of the favourite image to download.
        save_path (str): The base path where to save the downloaded image (directory + base filename).
        cookies (dict, optional): Optional cookies to use for authenticated requests.

    Returns:
        str: The filepath where the favourite image was downloaded, or None if failed.
        bool: True if the image was already downloaded, False otherwise.
    """
    # Get the image url
    response = requests.get(url, cookies=cookies)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')

    # Check for login screen
    if "Login Required" in soup.text:
        print(f"Login required to download image: {url}")
        return None, False

    # Get the image download section
    download_div = soup.find('div', class_='download')
    if not download_div:
        # Fallback to mobile download link if desktop download section is not found
        download_link = soup.find('a', string=lambda text: text and 'download' in text.lower(), href=True)
        if download_link:
            favourites_url = download_link.get('href')
            if not favourites_url:
                return None, False
            if favourites_url.startswith('//'):
                favourites_url = 'https:' + favourites_url
        else:
            return None, False
    else:
        # Get image url
        link = download_div.find('a')
        if not link:
            return None, False
        favourites_url = link.get('href')
        if not favourites_url:
            return None, False
        elif favourites_url.startswith('//'):
            favourites_url = 'https:' + favourites_url

    # Get image details
    submission_details = soup.find('div', class_='submission-id-sub-container')
    if not submission_details:
        return None, False

    # Get title
    title_block = submission_details.find('div', class_='submission-title')
    title_p = title_block.find('p') if title_block else None
    title = title_p.text.strip() if title_p else 'untitled'
    title = sanitize_filename(title)[:50]  # Truncate to 50 chars

    # Get artist
    username_block = (submission_details.find('span', class_='c-usernameBlockSimple'))
    username = username_block.find('a', href=True).text.strip() if username_block else 'unknown_user'
    username = sanitize_filename(username)

    # Get file extension, handling URLs with query parameters
    parsed_url = urlparse(favourites_url)
    _, ext = os.path.splitext(parsed_url.path)
    if not ext:
        return None, False # Exit; not a file

    # Create folder for artist if none existent
    if not os.path.exists(os.path.join(save_path, username)):
        os.makedirs(os.path.join(save_path, username))
        print(f"Created directory for {username}")

    # Construct filename
    filename = f"{title}{ext}"
    actual_save_path = os.path.join(save_path, username, filename)

    # Check if image already exists
    if os.path.exists(actual_save_path):
        return actual_save_path, True

    # Download the image
    image_response = requests.get(favourites_url, cookies=cookies)
    image_response.raise_for_status()

    with open(actual_save_path, 'wb') as f:
        f.write(image_response.content)

    return actual_save_path, False


def load_cookies(cookie_file):
    """
    Load cookies from a Netscape cookies file.

    Netscape cookies file format (tab-separated):
    domain, flag, path, secure, expiration, name, value

    Args:
        cookie_file (str): Path to the Netscape cookies file.

    Returns:
        dict: Dictionary of cookies (name -> value), or None if file not found or invalid.
    """
    if not cookie_file or not os.path.exists(cookie_file):
        return None
    
    cookies = {}
    try:
        with open(cookie_file, 'r') as f:
            for line in f:
                # Skip header lines and empty lines
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                # Parse tab-separated values
                parts = line.split('\t')
                if len(parts) >= 7:
                    # Extract cookie name and value
                    # Format: domain, flag, path, secure, expiration, name, value
                    cookie_name = parts[5]
                    cookie_value = parts[6]
                    cookies[cookie_name] = cookie_value
        
        return cookies if cookies else None
    except IOError as e:
        print(f"Warning: Error while trying to load cookies from {cookie_file}: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(
        prog='fa-fave-downloader',
        description="FurAffinity favourite downloader")
    parser.add_argument('--username', '-u',
                        help='REQUIRED: Fur Affinity username to download favorites from', required=True)
    parser.add_argument('--save-path', '-p', default=os.path.join(os.getcwd(), 'output'),
                        help='Directory to save images (default: ./save)')
    parser.add_argument('--cookie', '-c', help='Optional: path to your FA cookie file for authenticated access')
    parser.add_argument('--version', '-v', action='version', version=f'%(prog)s {__version__}')
    args = parser.parse_args()

    print("FA Fave Downloader")
    print(f"Version: {__version__}")
    print("--------------------------------")
    print("Downloading favourites from", args.username)

    # For the save path is provided, make sure it exists
    save_path = args.save_path
    if not os.path.exists(save_path):
        os.makedirs(save_path)

    # Load cookies if provided
    cookies = load_cookies(cookie_file=args.cookie) if args.cookie else None
    if args.cookie and cookies is None:
        print(f"Error: Unable to load cookies from {args.cookie}")
        exit(1)
    elif args.cookie and cookies is not None:
        print("Successfully loaded cookies from", args.cookie)

    # Check first page for favourites
    urls = get_favorite_image_urls(username=args.username, cookies=cookies)
    if len(urls) == 0:
        print(f"No favourite images found for {args.username}")
        exit(0)

    # Downloads the images to the save path
    i = 0
    for url in urls:
        i += 1
        print(f"Downloading image {i}/{len(urls)} from {url} ...")

        result, duplicate = download_favorite(url=url, save_path=save_path, cookies=cookies)
        if duplicate:
            print(f"Image already downloaded image {i}/{len(urls)}: {result}")
        elif result:
            print(f"Downloaded image {i}/{len(urls)}: {result}")
        else:
            print(f"Failed to download image {i}/{len(urls)}: {url}")

    print("Download complete.")

if __name__ == '__main__':
    main()