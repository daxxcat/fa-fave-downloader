import unittest
from unittest.mock import patch, mock_open, MagicMock
import os
import tempfile
from fa_fave_downloader.cli import (
    sanitize_filename, get_favorite_image_urls, download_favorite, main,
    get_favorite_image_urls_inner, get_next_page_url
)


class TestCli(unittest.TestCase):
    """Unit tests for the CLI module functions."""

    # ==================== sanitize_filename tests ====================
    def test_sanitize_filename(self):
        """Test the sanitize_filename function with various inputs to ensure proper sanitization."""
        # Test basic sanitization
        self.assertEqual(sanitize_filename("hello world"), "hello-world")
        self.assertEqual(sanitize_filename("hello   world"), "hello-world")
        self.assertEqual(sanitize_filename("hello@world!"), "hello_world_")
        self.assertEqual(sanitize_filename("hello.world"), "hello.world")
        self.assertEqual(sanitize_filename("hello/world\\test"), "hello_world_test")

    def test_sanitize_filename_with_multiple_dots(self):
        """Test sanitize_filename with filenames containing multiple dots."""
        self.assertEqual(sanitize_filename("1288659508.sidian_pawscomic"), "1288659508.sidian_pawscomic")
        self.assertEqual(sanitize_filename("file.name.with.dots"), "file.name.with.dots")

    def test_sanitize_filename_special_chars(self):
        """Test sanitize_filename with various special characters."""
        self.assertEqual(sanitize_filename("test@#$%^&*"), "test_______")
        self.assertEqual(sanitize_filename("test-file_name"), "test-file_name")

    # ==================== get_favorite_image_urls_inner tests ====================
    def test_get_favorite_image_urls_inner(self):
        """Test the inner helper function that extracts URLs from a gallery favorites section."""
        from bs4 import BeautifulSoup
        
        html = '''
        <section id="gallery-favorites">
            <a href="/view/123/"><img src="image1.jpg"></a>
            <a href="/view/456/"><img src="image2.jpg"></a>
            <a href="/view/789/"></a>  <!-- no img -->
        </section>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        gallery = soup.find('section', id='gallery-favorites')
        
        urls = get_favorite_image_urls_inner(gallery)
        expected = [
            "https://www.furaffinity.net/view/123/",
            "https://www.furaffinity.net/view/456/",
        ]
        self.assertEqual(urls, expected)

    def test_get_favorite_image_urls_inner_external_links(self):
        """Test that external links are preserved correctly."""
        from bs4 import BeautifulSoup
        
        html = '''
        <section id="gallery-favorites">
            <a href="https://external.com/image.jpg"><img src="image.jpg"></a>
        </section>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        gallery = soup.find('section', id='gallery-favorites')
        
        urls = get_favorite_image_urls_inner(gallery)
        self.assertEqual(urls, ["https://external.com/image.jpg"])

    # ==================== get_next_page_url tests ====================
    @patch('fa_fave_downloader.cli.requests.get')
    def test_get_next_page_url_found(self, mock_get):
        """Test finding the next page URL when a Next button exists."""
        mock_response = MagicMock()
        mock_response.text = '''
        <html>
        <form action="/favorites/testuser/12345/next" method="get">
            <button class="button standard" type="submit">Next</button>
        </form>
        </html>
        '''
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        next_url = get_next_page_url("https://www.furaffinity.net/favorites/testuser/")
        self.assertEqual(next_url, "https://www.furaffinity.net/favorites/testuser/12345/next")

    @patch('fa_fave_downloader.cli.requests.get')
    def test_get_next_page_url_not_found(self, mock_get):
        """Test that None is returned when no Next button exists."""
        mock_response = MagicMock()
        mock_response.text = '<html></html>'
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        next_url = get_next_page_url("https://www.furaffinity.net/favorites/testuser/")
        self.assertIsNone(next_url)

    @patch('fa_fave_downloader.cli.requests.get')
    def test_get_next_page_url_with_full_url(self, mock_get):
        """Test that full URLs are preserved."""
        mock_response = MagicMock()
        mock_response.text = '''
        <html>
        <form action="https://www.furaffinity.net/favorites/testuser/12345/next" method="get">
            <button class="button standard" type="submit">Next</button>
        </form>
        </html>
        '''
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        next_url = get_next_page_url("https://www.furaffinity.net/favorites/testuser/")
        self.assertEqual(next_url, "https://www.furaffinity.net/favorites/testuser/12345/next")

    # ==================== get_favorite_image_urls tests ====================
    @patch('fa_fave_downloader.cli.requests.get')
    @patch('fa_fave_downloader.cli.get_next_page_url')
    def test_get_favorite_image_urls(self, mock_get_next, mock_get):
        """Test extracting favorite image URLs from the gallery-favorites section of the HTML."""
        mock_response = MagicMock()
        mock_response.text = '''
        <html>
        <section id="gallery-favorites">
            <a href="/view/123/"><img src="image1.jpg"></a>
            <a href="/view/456/"><img src="image2.jpg"></a>
            <a href="https://external.com"><img src="image3.jpg"></a>
            <a href="/view/789/"></a>  <!-- no img -->
        </section>
        </html>
        '''
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        mock_get_next.return_value = None  # No next page

        urls = get_favorite_image_urls("testuser")
        expected = [
            "https://www.furaffinity.net/view/123/",
            "https://www.furaffinity.net/view/456/",
            "https://external.com"
        ]
        self.assertEqual(urls, expected)

    @patch('fa_fave_downloader.cli.requests.get')
    @patch('fa_fave_downloader.cli.get_next_page_url')
    def test_get_favorite_image_urls_no_favorites(self, mock_get_next, mock_get):
        """Test that empty list is returned when no gallery-favorites section exists."""
        mock_response = MagicMock()
        mock_response.text = '<html></html>'
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        mock_get_next.return_value = None

        urls = get_favorite_image_urls("testuser")
        self.assertEqual(urls, [])

    @patch('fa_fave_downloader.cli.requests.get')
    @patch('fa_fave_downloader.cli.get_next_page_url')
    def test_get_favorite_image_urls_with_pagination(self, mock_get_next, mock_get):
        """Test that pagination is handled correctly when multiple pages exist."""
        # First page response
        first_page_response = MagicMock()
        first_page_response.text = '''
        <html>
        <section id="gallery-favorites">
            <a href="/view/123/"><img src="image1.jpg"></a>
            <a href="/view/456/"><img src="image2.jpg"></a>
        </section>
        </html>
        '''
        first_page_response.raise_for_status.return_value = None

        # Second page response
        second_page_response = MagicMock()
        second_page_response.text = '''
        <html>
        <section id="gallery-favorites">
            <a href="/view/789/"><img src="image3.jpg"></a>
        </section>
        </html>
        '''
        second_page_response.raise_for_status.return_value = None

        # Mock requests.get to return different responses
        mock_get.side_effect = [first_page_response, second_page_response]
        
        # Mock get_next_page_url to return next page on first call, None on second
        mock_get_next.side_effect = [
            "https://www.furaffinity.net/favorites/testuser/page2/",
            None
        ]

        urls = get_favorite_image_urls("testuser")
        expected = [
            "https://www.furaffinity.net/view/123/",
            "https://www.furaffinity.net/view/456/",
            "https://www.furaffinity.net/view/789/",
        ]
        self.assertEqual(urls, expected)

    # ==================== download_favorite tests ====================
    @patch('fa_fave_downloader.cli.requests.get')
    @patch('fa_fave_downloader.cli.os.path.exists')
    @patch('fa_fave_downloader.cli.os.makedirs')
    @patch('builtins.open', new_callable=mock_open)
    def test_download_favorite(self, mock_file, mock_makedirs, mock_exists, mock_get):
        """Test downloading a favorite image, including parsing HTML, creating directories, and writing files."""
        mock_page_response = MagicMock()
        mock_page_response.text = '''
        <html>
        <div class="download">
            <a href="//d.facdn.net/art/artist/1234567890.jpg"></a>
        </div>
        <div class="submission-id-sub-container">
            <div class="submission-title">
                <p>Test Title</p>
            </div>
            <span class="c-usernameBlockSimple">
                <a href="/user/artist">Artist</a>
            </span>
        </div>
        </html>
        '''
        mock_page_response.raise_for_status.return_value = None

        mock_image_response = MagicMock()
        mock_image_response.content = b'fake image data'
        mock_image_response.raise_for_status.return_value = None

        def mock_get_side_effect(url):
            if 'view' in url:
                return mock_page_response
            else:
                return mock_image_response

        mock_get.side_effect = mock_get_side_effect
        mock_exists.return_value = False

        with tempfile.TemporaryDirectory() as temp_dir:
            result, is_duplicate = download_favorite("https://www.furaffinity.net/view/123/", temp_dir)
            expected_path = os.path.join(temp_dir, "Artist", "Test-Title.jpg")
            self.assertEqual(result, expected_path)
            self.assertFalse(is_duplicate)

    @patch('fa_fave_downloader.cli.requests.get')
    def test_download_favorite_no_download_div(self, mock_get):
        """Test that download_favorite returns None when no download section is found."""
        mock_response = MagicMock()
        mock_response.text = '<html></html>'
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result, is_duplicate = download_favorite("https://www.furaffinity.net/view/123/", "/tmp")
        self.assertIsNone(result)
        self.assertFalse(is_duplicate)

    @patch('fa_fave_downloader.cli.requests.get')
    def test_download_favorite_login_required(self, mock_get):
        """Test that download_favorite handles login required pages."""
        mock_response = MagicMock()
        mock_response.text = '<html>Login Required</html>'
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result, is_duplicate = download_favorite("https://www.furaffinity.net/view/123/", "/tmp")
        self.assertIsNone(result)
        self.assertFalse(is_duplicate)

    @patch('fa_fave_downloader.cli.requests.get')
    def test_download_favorite_with_fallback_download_link(self, mock_get):
        """Test that download_favorite uses fallback Download anchor link when div is missing."""
        mock_page_response = MagicMock()
        mock_page_response.text = '''
        <html>
        <a href="//d.facdn.net/download/file.jpg">Download</a>
        <div class="submission-id-sub-container">
            <div class="submission-title">
                <p>Test Title</p>
            </div>
            <span class="c-usernameBlockSimple">
                <a href="/user/artist">Artist</a>
            </span>
        </div>
        </html>
        '''
        mock_page_response.raise_for_status.return_value = None

        mock_image_response = MagicMock()
        mock_image_response.content = b'image data'
        mock_image_response.raise_for_status.return_value = None

        def mock_get_side_effect(url):
            if 'view' in url:
                return mock_page_response
            else:
                return mock_image_response

        mock_get.side_effect = mock_get_side_effect

        with patch('fa_fave_downloader.cli.os.path.exists', return_value=False):
            with patch('fa_fave_downloader.cli.os.makedirs'):
                with patch('builtins.open', mock_open()):
                    result, is_duplicate = download_favorite("https://www.furaffinity.net/view/123/", "/tmp")
                    self.assertIsNotNone(result)
                    self.assertFalse(is_duplicate)

    @patch('fa_fave_downloader.cli.requests.get')
    @patch('fa_fave_downloader.cli.os.path.exists')
    def test_download_favorite_already_exists(self, mock_exists, mock_get):
        """Test that download_favorite returns duplicate flag when file already exists."""
        mock_page_response = MagicMock()
        mock_page_response.text = '''
        <html>
        <div class="download">
            <a href="//d.facdn.net/art/artist/file.jpg"></a>
        </div>
        <div class="submission-id-sub-container">
            <div class="submission-title">
                <p>Test Title</p>
            </div>
            <span class="c-usernameBlockSimple">
                <a href="/user/artist">Artist</a>
            </span>
        </div>
        </html>
        '''
        mock_page_response.raise_for_status.return_value = None
        mock_get.return_value = mock_page_response
        mock_exists.side_effect = [False, True]  # First False for dir, then True for file

        with patch('fa_fave_downloader.cli.os.makedirs'):
            result, is_duplicate = download_favorite("https://www.furaffinity.net/view/123/", "/tmp")
            self.assertIsNotNone(result)
            self.assertTrue(is_duplicate)

    @patch('fa_fave_downloader.cli.requests.get')
    def test_download_favorite_no_extension(self, mock_get):
        """Test that download_favorite returns None when file has no extension."""
        mock_response = MagicMock()
        mock_response.text = '''
        <html>
        <div class="download">
            <a href="//d.facdn.net/art/artist/filename"></a>
        </div>
        <div class="submission-id-sub-container">
            <div class="submission-title">
                <p>Test Title</p>
            </div>
            <span class="c-usernameBlockSimple">
                <a href="/user/artist">Artist</a>
            </span>
        </div>
        </html>
        '''
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result, is_duplicate = download_favorite("https://www.furaffinity.net/view/123/", "/tmp")
        self.assertIsNone(result)
        self.assertFalse(is_duplicate)

    # ==================== main function tests ====================
    @patch('fa_fave_downloader.cli.argparse.ArgumentParser.parse_args')
    @patch('fa_fave_downloader.cli.get_favorite_image_urls')
    @patch('fa_fave_downloader.cli.download_favorite')
    @patch('fa_fave_downloader.cli.os.path.exists')
    @patch('fa_fave_downloader.cli.os.makedirs')
    def test_main(self, mock_makedirs, mock_exists, mock_download, mock_get_urls, mock_parse_args):
        """Test the main CLI function to ensure it parses arguments and calls download functions."""
        mock_parse_args.return_value = MagicMock(username='testuser', save_path='/tmp')
        mock_get_urls.return_value = ["url1", "url2"]
        mock_download.side_effect = [("path1", False), ("path2", False)]
        mock_exists.return_value = False

        main()

        mock_get_urls.assert_called_once_with('testuser')
        self.assertEqual(mock_download.call_count, 2)

    @patch('fa_fave_downloader.cli.argparse.ArgumentParser.parse_args')
    @patch('fa_fave_downloader.cli.get_favorite_image_urls')
    @patch('fa_fave_downloader.cli.os.path.exists')
    @patch('fa_fave_downloader.cli.os.makedirs')
    def test_main_no_favorites(self, mock_makedirs, mock_exists, mock_get_urls, mock_parse_args):
        """Test that main exits gracefully when no favorites are found."""
        mock_parse_args.return_value = MagicMock(username='testuser', save_path='/tmp')
        mock_get_urls.return_value = []
        mock_exists.return_value = True

        with self.assertRaises(SystemExit):
            main()

    @patch('fa_fave_downloader.cli.argparse.ArgumentParser.parse_args')
    @patch('fa_fave_downloader.cli.get_favorite_image_urls')
    @patch('fa_fave_downloader.cli.download_favorite')
    @patch('fa_fave_downloader.cli.os.path.exists')
    @patch('fa_fave_downloader.cli.os.makedirs')
    def test_main_with_duplicate_files(self, mock_makedirs, mock_exists, mock_download, mock_get_urls, mock_parse_args):
        """Test main handling of duplicate files."""
        mock_parse_args.return_value = MagicMock(username='testuser', save_path='/tmp')
        mock_get_urls.return_value = ["url1", "url2"]
        mock_download.side_effect = [("path1", True), ("path2", False)]  # First is duplicate
        mock_exists.return_value = False

        main()

        self.assertEqual(mock_download.call_count, 2)
        self.assertEqual(mock_download.call_count, 2)


if __name__ == "__main__":
    unittest.main()
