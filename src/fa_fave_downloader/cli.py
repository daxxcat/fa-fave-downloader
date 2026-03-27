#!/usr/bin/env python3
"""
Command-line interface for FA Fave Downloader.
"""
import argparse
import os
import re

import requests
from bs4 import BeautifulSoup

# Constants
FA_URL = "https://www.furaffinity.net"


def get_favorite_image_urls(username):
    """
    Retrieve the HTML page for the user's favorites and extract image URLs from the gallery-section.

    Args:
        username (str): The Fur Affinity username.

    Returns:
        list: List of image URLs found in the gallery-favorites section.
    """
    url = f"{FA_URL}/favorites/{username}/"
    response = requests.get(url)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')
    gallery_favorites = soup.find('section', id='gallery-favorites')
    if not gallery_favorites:
        return []

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


def sanitize_filename(name):
    """Sanitize filename by replacing invalid characters with underscores and consecutive spaces with a single dash."""
    # First replace invalid characters with underscores
    name = re.sub(r'[^\w\-_\. ]', '_', name)
    # Replace consecutive spaces with a single dash
    name = re.sub(r'\s+', '-', name)
    return name


def download_favorite(url, save_path):
    """
    Download the favourite image from the url section.

    Args:
        url (str): The url of the favourite image to download.
        save_path (str): The base path where to save the downloaded image (directory + base filename).

    Returns:
        str: The filepath where the favourite image was downloaded, or None if failed.
    """
    # Get the image url
    response = requests.get(url)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')

    # Get the image download section
    download_div = soup.find('div', class_='download')
    if not download_div:
        return None
    # Get image url
    favourites_url = download_div.find('a').get('href')
    if not favourites_url:
        return None
    elif favourites_url.startswith('//'):
        favourites_url = 'https:' + favourites_url

    # Get image details
    submission_details = soup.find('div', class_='submission-id-sub-container')
    if not submission_details:
        return None

    # Get title
    title_block = submission_details.find('div', class_='submission-title')
    title_p = title_block.find('p') if title_block else None
    title = title_p.text.strip() if title_p else 'untitled'
    title = sanitize_filename(title)[:50]  # Truncate to 50 chars

    # Get artist
    username_block = (submission_details.find('span', class_='c-usernameBlockSimple'))
    username = username_block.find('a', href=True).text.strip() if username_block else 'unknown_user'
    username = sanitize_filename(username)

    # Get file extension
    _, ext = os.path.splitext(favourites_url)
    if not ext:
        return None  # Exit; not a file

    # Create folder for artist if none existent
    if not os.path.exists(os.path.join(save_path, username)):
        os.makedirs(os.path.join(save_path, username))
        print(f"Created directory for {username}")

    # Construct filename
    filename = f"{title}{ext}"
    actual_save_path = os.path.join(save_path, username, filename)

    # Download the image
    image_response = requests.get(favourites_url)
    image_response.raise_for_status()

    with open(actual_save_path, 'wb') as f:
        f.write(image_response.content)

    return actual_save_path


def main():
    parser = argparse.ArgumentParser(
        prog='fa-fave-downloader',
        description="FurAffinity favourite downloader")
    parser.add_argument('--username', '-u',
                        help='REQUIRED: Fur Affinity username to download favorites from', required=True)
    parser.add_argument('--save-path', '-p', default=os.path.join(os.getcwd(), 'output'),
                        help='Directory to save images (default: ./save)')
    args = parser.parse_args()

    print("FA Fave Downloader")
    save_path = args.save_path
    if not os.path.exists(save_path):
        os.makedirs(save_path)

    urls = get_favorite_image_urls(args.username)
    print(f"Found {len(urls)} image URLs:")
    for url in urls[:5]:  # Print first 5
        print(url)

    # Check if provided path is real, and creates if not
    if not os.path.exists(args.save_path):
        os.makedirs(args.save_path)

    # Downloads the images to the save path
    i = 0
    for url in urls:
        i += 1
        print(f"Downloading image {i}/{len(urls)} from {url} ...")

        result = download_favorite(url, save_path)
        if result:
            print(f"Downloaded image {i}/{len(urls)}: {result}")
        else:
            print(f"Failed to download image {i}/{len(urls)}: {url}")


if __name__ == "__main__":
    main()
