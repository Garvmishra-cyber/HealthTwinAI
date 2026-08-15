import os
import gc
import re

import pytesseract
from PIL import Image, ImageOps, ImageFilter
import fitz


# ============================================================
# TESSERACT CONFIGURATION
# ============================================================

if os.name == "nt":

    # Windows
    windows_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

    if os.path.exists(windows_path):
        pytesseract.pytesseract.tesseract_cmd = windows_path

else:

    # Linux / Render
    pytesseract.pytesseract.tesseract_cmd = "tesseract"


# ============================================================
# OCR SETTINGS
# ============================================================

PDF_RENDER_SCALE = 1.5

# 6 = uniform block of text
TESSERACT_CONFIG = "--psm 6"


# ============================================================
# IMAGE PREPROCESSING
# ============================================================

def preprocess_image(image):
    """
    Prepare image for OCR.

    Keeps the original image untouched.
    """

    processed = None

    try:

        processed = image.convert("RGB")

        # Grayscale
        processed = ImageOps.grayscale(
            processed
        )

        # Slight contrast improvement
        processed = ImageOps.autocontrast(
            processed
        )

        # Light sharpening
        processed = processed.filter(
            ImageFilter.SHARPEN
        )

        return processed

    except Exception as error:

        print(
            "IMAGE PREPROCESSING ERROR:",
            error
        )

        return image


# ============================================================
# CLEAN OCR TEXT
# ============================================================

def clean_ocr_text(text):

    if not text:
        return ""

    text = str(text)

    # Normalize common OCR characters
    replacements = {
        "\x0c": "\n",
        "\r\n": "\n",
        "\r": "\n",
        "µ": "u",
        "μ": "u",
        "×": "x",
        "–": "-",
        "—": "-",
        "−": "-",
    }

    for old, new in replacements.items():

        text = text.replace(
            old,
            new
        )

    # Remove excessive spaces
    lines = []

    for line in text.splitlines():

        line = re.sub(
            r"[ \t]+",
            " ",
            line
        ).strip()

        if line:

            lines.append(
                line
            )

    return "\n".join(
        lines
    ).strip()


# ============================================================
# IMAGE OCR
# ============================================================

def extract_text_from_image(image_path):

    image = None
    processed = None

    try:

        print(
            "Opening image..."
        )

        image = Image.open(
            image_path
        )

        print(
            "IMAGE SIZE:",
            image.size
        )

        # ----------------------------------------------------
        # First OCR pass
        # Original image
        # ----------------------------------------------------

        original_text = pytesseract.image_to_string(
            image.convert("RGB"),
            config=TESSERACT_CONFIG
        )

        original_text = clean_ocr_text(
            original_text
        )

        # ----------------------------------------------------
        # Second OCR pass
        # Preprocessed image
        # ----------------------------------------------------

        processed = preprocess_image(
            image
        )

        processed_text = pytesseract.image_to_string(
            processed,
            config=TESSERACT_CONFIG
        )

        processed_text = clean_ocr_text(
            processed_text
        )

        # ----------------------------------------------------
        # Choose the better result
        #
        # Health reports normally contain useful keywords.
        # ----------------------------------------------------

        health_keywords = [
            "hemoglobin",
            "haemoglobin",
            "rbc",
            "wbc",
            "wec",
            "platelet",
            "mch",
            "mcv",
            "mchc",
            "rdw",
            "hematocrit",
            "pcv",
            "glucose",
            "cholesterol",
            "triglycerides",
            "creatinine",
            "bilirubin",
            "thyroid",
            "tsh",
            "esr",
            "crp",
        ]

        original_lower = original_text.lower()
        processed_lower = processed_text.lower()

        original_score = sum(
            1
            for keyword in health_keywords
            if keyword in original_lower
        )

        processed_score = sum(
            1
            for keyword in health_keywords
            if keyword in processed_lower
        )

        if processed_score > original_score:

            final_text = processed_text

        else:

            final_text = original_text

        print(
            "OCR KEYWORD SCORE:",
            original_score,
            processed_score
        )

        print(
            "IMAGE OCR SUCCESS"
        )

        return final_text

    except Exception as error:

        print(
            "IMAGE OCR ERROR:",
            error
        )

        return ""

    finally:

        if processed is not None:

            try:
                processed.close()

            except Exception:
                pass

        if image is not None:

            try:
                image.close()

            except Exception:
                pass

        processed = None
        image = None

        gc.collect()


# ============================================================
# NORMAL PDF TEXT EXTRACTION
# ============================================================

def extract_normal_pdf_text(document):

    all_text = []

    try:

        for page_number in range(
            len(document)
        ):

            page = None

            try:

                page = document.load_page(
                    page_number
                )

                text = page.get_text(
                    "text"
                )

                if text and text.strip():

                    all_text.append(
                        text.strip()
                    )

            finally:

                page = None

        return "\n\n".join(
            all_text
        ).strip()

    except Exception as error:

        print(
            "NORMAL PDF TEXT ERROR:",
            error
        )

        return ""

    finally:

        gc.collect()


# ============================================================
# OCR ONE PDF PAGE
# ============================================================

def ocr_pdf_page(
    document,
    page_number
):

    page = None
    pix = None
    image = None
    processed = None

    try:

        print(
            f"Rendering PDF page {page_number + 1}..."
        )

        page = document.load_page(
            page_number
        )

        # ----------------------------------------------------
        # Render one page only
        # ----------------------------------------------------

        pix = page.get_pixmap(
            matrix=fitz.Matrix(
                PDF_RENDER_SCALE,
                PDF_RENDER_SCALE
            ),
            colorspace=fitz.csRGB,
            alpha=False
        )

        image = Image.frombytes(
            "RGB",
            (
                pix.width,
                pix.height
            ),
            pix.samples
        )

        # ----------------------------------------------------
        # Preprocess
        # ----------------------------------------------------

        processed = preprocess_image(
            image
        )

        # ----------------------------------------------------
        # OCR
        # ----------------------------------------------------

        text = pytesseract.image_to_string(
            processed,
            config=TESSERACT_CONFIG
        )

        return clean_ocr_text(
            text
        )

    except Exception as error:

        print(
            f"OCR ERROR ON PAGE {page_number + 1}:",
            error
        )

        return ""

    finally:

        if processed is not None:

            try:
                processed.close()

            except Exception:
                pass

        if image is not None:

            try:
                image.close()

            except Exception:
                pass

        processed = None
        image = None
        pix = None
        page = None

        gc.collect()


# ============================================================
# PDF OCR EXTRACTION
# ============================================================

def extract_text_from_pdf(pdf_path):

    document = None

    try:

        print(
            "Opening PDF..."
        )

        document = fitz.open(
            pdf_path
        )

        page_count = len(
            document
        )

        print(
            "PDF PAGES:",
            page_count
        )

        # ====================================================
        # FIRST TRY NORMAL TEXT
        # ====================================================

        normal_text = extract_normal_pdf_text(
            document
        )

        if normal_text:

            print(
                "PDF TEXT EXTRACTION SUCCESS"
            )

            return clean_ocr_text(
                normal_text
            )

        # ====================================================
        # SCANNED PDF
        # ====================================================

        print(
            "No embedded PDF text found."
        )

        print(
            "Starting PDF OCR..."
        )

        ocr_pages = []

        for page_number in range(
            page_count
        ):

            print(
                f"OCR PAGE {page_number + 1}/{page_count}"
            )

            page_text = ocr_pdf_page(
                document,
                page_number
            )

            if page_text:

                ocr_pages.append(
                    page_text
                )

            gc.collect()

        final_text = "\n\n".join(
            ocr_pages
        ).strip()

        if final_text:

            print(
                "PDF OCR SUCCESS"
            )

        else:

            print(
                "PDF OCR returned no text."
            )

        return final_text

    except Exception as error:

        print(
            "PDF EXTRACTION ERROR:",
            error
        )

        return ""

    finally:

        if document is not None:

            try:
                document.close()

            except Exception:
                pass

        document = None

        gc.collect()


# ============================================================
# MAIN OCR FUNCTION
# ============================================================

def extract_text(file_path):

    if not file_path:

        print(
            "OCR ERROR: Empty file path"
        )

        return ""

    if not os.path.exists(
        file_path
    ):

        print(
            "FILE NOT FOUND:",
            file_path
        )

        return ""

    extension = os.path.splitext(
        file_path
    )[1].lower()

    print(
        "\n===================================="
    )

    print(
        "OCR FILE:",
        file_path
    )

    print(
        "FILE TYPE:",
        extension
    )

    print(
        "===================================="
    )

    # ========================================================
    # PDF
    # ========================================================

    if extension == ".pdf":

        return extract_text_from_pdf(
            file_path
        )

    # ========================================================
    # IMAGE
    # ========================================================

    if extension in [
        ".png",
        ".jpg",
        ".jpeg",
        ".bmp",
        ".tiff",
        ".webp"
    ]:

        return extract_text_from_image(
            file_path
        )

    # ========================================================
    # UNSUPPORTED
    # ========================================================

    print(
        "UNSUPPORTED FILE TYPE:",
        extension
    )

    return ""