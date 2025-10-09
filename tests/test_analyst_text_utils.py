from analyst.edgar import extract_section_texts
from analyst.summarize import top_sentences_tfidf


def test_top_sentences_tfidf_returns_k():
    text = "One. Two. Three. Four. Five."
    top = top_sentences_tfidf(text, k=3)
    assert len(top) == 3
    # They should be real sentences (non-empty)
    assert all(len(s) > 0 for s in top)


def test_extract_section_texts_basic_html():
    html = """
    <html><body>
      <h2>Item 7. Management's Discussion and Analysis</h2>
      <p>Revenue increased due to new products.</p>
      <p>Margins improved year over year.</p>

      <h2>Item 1A. Risk Factors</h2>
      <p>Supply chain disruptions may impact deliveries.</p>
      <p>Foreign exchange volatility is a risk.</p>
    </body></html>
    """
    sec = extract_section_texts(html)
    assert "Revenue increased" in sec["mdna"]
    assert "Supply chain disruptions" in sec["risk"]
