def normalize_company_id(value):
    return str(value or "").strip().lower()


def load_resume_pdf(path):
    from PyPDF2 import PdfReader

    reader = PdfReader(path)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text
