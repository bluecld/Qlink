import sys
from pathlib import Path
from PyPDF2 import PdfReader

pdf_path = Path(__file__).resolve().parents[1] / "Info" / "list of keypads.pdf"

if not pdf_path.exists():
    print("PDF not found at", pdf_path)
    sys.exit(2)

reader = PdfReader(str(pdf_path))
out = []
for i, page in enumerate(reader.pages):
    try:
        text = page.extract_text()
    except Exception as e:
        text = f"<<error extracting page {i}: {e}>>"
    out.append(f"--- page {i + 1} ---")
    out.append(text or "")

print("\n".join(out))
