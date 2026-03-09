"""Fixtures compartilhadas entre todos os testes."""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Cliente HTTP para testar a API FastAPI."""
    from backend.main import app
    return TestClient(app)


@pytest.fixture
def sample_html() -> str:
    """HTML simples simulando saída do Docling."""
    return """<!DOCTYPE html>
<html><head><title>Test Document</title></head>
<body>
<h1>Introduction</h1>
<p>This is a test paragraph with relevant content.</p>
<h2>Methods</h2>
<p>The experiment was conducted using standard procedures.</p>
<ul><li>Item one</li><li>Item two</li></ul>
</body>
</html>"""


@pytest.fixture
def sample_pdf_bytes() -> bytes:
    """Bytes mínimos de um PDF válido."""
    return (
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\n"
        b"xref\n0 4\n"
        b"0000000000 65535 f\n"
        b"0000000009 00000 n\n"
        b"0000000058 00000 n\n"
        b"0000000115 00000 n\n"
        b"trailer<</Size 4/Root 1 0 R>>\n"
        b"startxref\n190\n%%EOF"
    )
