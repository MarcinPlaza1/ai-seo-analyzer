import pytest
from app.utils.text_processors import clean_text, extract_keywords

def test_clean_text_html():
    text = "<p>Test <b>tekst</b></p>"
    assert clean_text(text) == "Test tekst"

def test_clean_text_whitespace():
    text = "  Test    tekst\n\n  z   spacjami  "
    assert clean_text(text) == "Test tekst z spacjami"

def test_clean_text_empty():
    assert clean_text("") == ""
    assert clean_text("   ") == ""

def test_clean_text_complex():
    text = """
    <div>
        <h1>Nagłówek</h1>
        <p>Paragraf   z   wieloma    spacjami</p>
        <script>console.log('test');</script>
    </div>
    """
    assert clean_text(text) == "Nagłówek Paragraf z wieloma spacjami"

@pytest.mark.parametrize("text,expected", [
    ("<p>Test</p>", "Test"),
    ("Test    tekst", "Test tekst"),
    ("  Test  ", "Test"),
    ("<script>alert('test');</script>Tekst", "Tekst"),
])
def test_clean_text_parametrized(text, expected):
    assert clean_text(text) == expected

def test_extract_keywords_basic():
    text = "Test tekst do analizy"
    keywords = extract_keywords(text)
    assert "test" in keywords
    assert "tekst" in keywords
    assert "analizy" in keywords
    assert "test tekst" in keywords
    assert "tekst do" in keywords
    assert "do analizy" in keywords

def test_extract_keywords_min_length():
    text = "To jest test"
    keywords = extract_keywords(text, min_length=4)
    assert "to" not in keywords
    assert "jest" not in keywords
    assert "test" in keywords

def test_extract_keywords_max_words():
    text = "pierwszy drugi trzeci czwarty"
    keywords = extract_keywords(text, max_words=1)
    assert "pierwszy" in keywords
    assert "pierwszy drugi" not in keywords
    
    keywords = extract_keywords(text, max_words=3)
    assert "pierwszy drugi trzeci" in keywords

def test_extract_keywords_duplicates():
    text = "test test test"
    keywords = extract_keywords(text)
    assert keywords.count("test") == 1
    assert "test test" in keywords

def test_extract_keywords_case_sensitivity():
    text = "Test TEST test"
    keywords = extract_keywords(text)
    assert "test" in keywords
    assert "Test" not in keywords
    assert "TEST" not in keywords

def test_extract_keywords_empty():
    assert extract_keywords("") == []
    assert extract_keywords("   ") == []

@pytest.mark.parametrize("text,min_length,max_words,expected_in,expected_not_in", [
    ("test tekst", 3, 1, ["test", "tekst"], ["test tekst"]),
    ("krótki test", 6, 2, ["krótki"], ["test", "krótki test"]),
    ("a bb ccc", 2, 2, ["bb", "ccc", "bb ccc"], ["a"]),
])
def test_extract_keywords_parametrized(text, min_length, max_words, expected_in, expected_not_in):
    keywords = extract_keywords(text, min_length, max_words)
    for keyword in expected_in:
        assert keyword in keywords
    for keyword in expected_not_in:
        assert keyword not in keywords 