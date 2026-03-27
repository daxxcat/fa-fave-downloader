import unittest
from unittest.mock import patch, mock_open, MagicMock
import os
import tempfile
from fa_fave_downloader.cli import sanitize_filename, get_favorite_image_urls, download_favorite, main


class TestCli(unittest.TestCase):
    """Unit tests for the CLI module functions."""

    def test_sanitize_filename(self):
        """Test the sanitize_filename function with various inputs to ensure proper sanitization."""
        # Test basic sanitization
        self.assertEqual(sanitize_filename("hello world"), "hello-world")
        self.assertEqual(sanitize_filename("hello   world"), "hello-world")
        self.assertEqual(sanitize_filename("hello@world!"), "hello_world_")
        self.assertEqual(sanitize_filename("hello.world"), "hello.world")
        self.assertEqual(sanitize_filename("hello/world\\test"), "hello_world_test")

    @patch('fa_fave_downloader.cli.requests.get')
    def test_get_favorite_image_urls(self, mock_get):
        """Test extracting favorite image URLs from the gallery-favorites section of the HTML."""
        # Mock the response
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

        urls = get_favorite_image_urls("testuser")
        expected = [
            "https://www.furaffinity.net/view/123/",
            "https://www.furaffinity.net/view/456/",
            "https://external.com"
        ]
        self.assertEqual(urls, expected)

        # Test when no gallery-favorites
        mock_response.text = '<html></html>'
        urls = get_favorite_image_urls("testuser")
        self.assertEqual(urls, [])

    @patch('fa_fave_downloader.cli.requests.get')
    @patch('fa_fave_downloader.cli.os.path.exists')
    @patch('fa_fave_downloader.cli.os.makedirs')
    @patch('builtins.open', new_callable=mock_open)
    def test_download_favorite(self, mock_file, mock_makedirs, mock_exists, mock_get):
        """Test downloading a favorite image, including parsing HTML, creating directories, and writing files."""
        # Mock the page response
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

        # Mock the image response
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
            result = download_favorite("https://www.furaffinity.net/view/123/", temp_dir)
            expected_path = os.path.join(temp_dir, "Artist", "Test-Title.jpg")
            self.assertEqual(result, expected_path)

            # Check that makedirs was called
            mock_makedirs.assert_called_once_with(os.path.join(temp_dir, "Artist"))

            # Check that file was written
            mock_file.assert_called_once_with(expected_path, 'wb')
            mock_file().write.assert_called_once_with(b'fake image data')

    @patch('fa_fave_downloader.cli.requests.get')
    def test_download_favorite_no_download_div(self, mock_get):
        """Test that download_favorite returns None when the download div is missing."""
        mock_response = MagicMock()
        mock_response.text = '<html></html>'
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = download_favorite("https://www.furaffinity.net/view/123/", "/tmp")
        self.assertIsNone(result)

    @patch('fa_fave_downloader.cli.argparse.ArgumentParser.parse_args')
    @patch('fa_fave_downloader.cli.get_favorite_image_urls')
    @patch('fa_fave_downloader.cli.download_favorite')
    @patch('fa_fave_downloader.cli.os.path.exists')
    @patch('fa_fave_downloader.cli.os.makedirs')
    def test_main(self, mock_makedirs, mock_exists, mock_download, mock_get_urls, mock_parse_args):
        """Test the main CLI function to ensure it parses arguments and calls download functions."""
        mock_parse_args.return_value = MagicMock(username='testuser', save_path='/tmp')
        mock_get_urls.return_value = ["url1", "url2"]
        mock_download.return_value = "path1"
        mock_exists.return_value = False

        main()

        mock_get_urls.assert_called_once_with('testuser')
        self.assertEqual(mock_download.call_count, 2)


if __name__ == "__main__":
    unittest.main()
