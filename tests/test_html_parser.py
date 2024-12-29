import pytest
from typing import Dict, List
from app.utils.html_parser import HTMLParser

@pytest.fixture
def sample_html() -> str:
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="description" content="Test description">
        <meta property="og:title" content="Test title">
        <title>Test Page</title>
    </head>
    <body>
        <h1>Main Header</h1>
        <h2>Subheader 1</h2>
        <h2>Subheader 2</h2>
        <p>Some text content.</p>
        <img src="test.jpg" alt="Test image" title="Image title">
        <a href="https://example.com" title="Link title">Example link</a>
        <script>console.log('test');</script>
        <style>.test { color: red; }</style>
    </body>
    </html>
    """

@pytest.fixture
def parser(sample_html: str) -> HTMLParser:
    return HTMLParser(sample_html)

def test_get_meta_tags(parser: HTMLParser) -> None:
    meta_tags = parser.get_meta_tags()
    assert meta_tags['description'] == 'Test description'
    assert meta_tags['og:title'] == 'Test title'
    assert len(meta_tags) == 2

def test_get_headings(parser: HTMLParser) -> None:
    headings = parser.get_headings()
    assert headings['h1'] == ['Main Header']
    assert headings['h2'] == ['Subheader 1', 'Subheader 2']
    assert len(headings['h3']) == 0

def test_get_images(parser: HTMLParser) -> None:
    images = parser.get_images()
    assert len(images) == 1
    assert images[0]['src'] == 'test.jpg'
    assert images[0]['alt'] == 'Test image'
    assert images[0]['title'] == 'Image title'

def test_get_links(parser: HTMLParser) -> None:
    links = parser.get_links()
    assert len(links) == 1
    assert links[0]['href'] == 'https://example.com'
    assert links[0]['text'] == 'Example link'
    assert links[0]['title'] == 'Link title'

def test_get_text_content(parser: HTMLParser) -> None:
    text = parser.get_text_content()
    assert 'Main Header' in text
    assert 'Some text content' in text
    assert 'console.log' not in text  # script content should be removed
    assert '.test {' not in text  # style content should be removed

def test_empty_html() -> None:
    parser = HTMLParser('')
    assert parser.get_meta_tags() == {}
    assert all(len(h) == 0 for h in parser.get_headings().values())
    assert parser.get_images() == []
    assert parser.get_links() == []
    assert parser.get_text_content().strip() == ''

def test_malformed_html() -> None:
    malformed_html = '<p>Test</p><img><a>Link</a>'
    parser = HTMLParser(malformed_html)
    assert parser.get_images() == [{'src': '', 'alt': '', 'title': ''}]
    assert parser.get_links() == [{'href': '', 'text': 'Link', 'title': ''}]
    assert 'Test' in parser.get_text_content() 