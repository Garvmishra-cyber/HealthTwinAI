import os
import gc

import pytesseract
from PIL import Image
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

# Lower than the old 2x rendering to reduce Render memory usage.
PDF_RENDER_SCALE = 1.5

# OCR page configuration.
TESSERACT_CONFIG = "--psm 6"


# ============================================================
# IMAGE OCR
# ============================================================

def extract_text_from_image(image_path):

    image = None

    try:

        image = Image.open(image_path)

        image = image.convert("RGB")

        text = pytesseract.image_to_string(
            image,
            config=TESSERACT_CONFIG
        )

        return text.strip()

    except Exception as error:

        print(
            "IMAGE OCR ERROR:",
            error
        )

        return ""

    finally:

        # Explicitly release image memory.
        if image is not None:

            try:
                image.close()

            except Exception:
                pass

        gc.collect()


# ============================================================
# PDF NORMAL TEXT EXTRACTION
# ============================================================

def extract_normal_pdf_text(document):

    all_text = []

    try:

        for page_number in range(len(document)):

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

                # Release page reference.
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

def ocr_pdf_page(document, page_number):

    page = None
    pix = None
    image = None

    try:

        # ----------------------------------------------------
        # Load only ONE page
        # ----------------------------------------------------

        page = document.load_page(
            page_number
        )

        # ----------------------------------------------------
        # Render at 1.5x instead of 2x
        # This significantly reduces memory usage.
        # ----------------------------------------------------

        pix = page.get_pixmap(
            matrix=fitz.Matrix(
                PDF_RENDER_SCALE,
                PDF_RENDER_SCALE
            ),
            colorspace=fitz.csRGB,
            alpha=False
        )

        # ----------------------------------------------------
        # Convert pixmap to PIL image
        # ----------------------------------------------------

        image = Image.frombytes(
            "RGB",
            (
                pix.width,
                pix.height
            ),
            pix.samples
        )

        # ----------------------------------------------------
        # OCR
        # ----------------------------------------------------

        text = pytesseract.image_to_string(
            image,
            config=TESSERACT_CONFIG
        )

        return text.strip()

    except Exception as error:

        print(
            f"OCR ERROR ON PAGE {page_number + 1}:",
            error
        )

        return ""

    finally:

        # ----------------------------------------------------
        # IMPORTANT:
        # Explicitly release large objects after EVERY page.
        # ----------------------------------------------------

        if image is not None:

            try:
                image.close()

            except Exception:
                pass

        image = None
        pix = None
        page = None

        # Force Python garbage collection.
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
        # FIRST:
        # TRY NORMAL PDF TEXT EXTRACTION
        # ====================================================

        normal_text = extract_normal_pdf_text(
            document
        )

        if normal_text:

            print(
                "PDF TEXT EXTRACTION SUCCESS"
            )

            return normal_text

        # ====================================================
        # SECOND:
        # SCANNED PDF
        # USE MEMORY-SAFE OCR
        # ====================================================

        print(
            "No embedded PDF text found."
        )

        print(
            "Starting memory-safe OCR..."
        )

        ocr_text = []

        # ----------------------------------------------------
        # Process ONE page at a time.
        # ----------------------------------------------------

        for page_number in range(
            page_count
        ):

            print(
                f"OCR PAGE {page_number + 1}/{page_count}"
            )

            text = ocr_pdf_page(
                document,
                page_number
            )

            if text:

                ocr_text.append(
                    text
                )

            # ------------------------------------------------
            # Force cleanup between pages.
            # ------------------------------------------------

            gc.collect()

        # ====================================================
        # COMBINE OCR TEXT
        # ====================================================

        final_text = "\n\n".join(
            ocr_text
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

        # ----------------------------------------------------
        # Close PDF document.
        # ----------------------------------------------------

        if document is not None:

            try:
                document.close()

            except Exception:
                pass

        document = None

        # ----------------------------------------------------
        # Final memory cleanup.
        # ----------------------------------------------------

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

    if not os.path.exists(file_path):

        print(
            "FILE NOT FOUND:",
            file_path
        )

        return ""

    extension = os.path.splitext(
        file_path
    )[1].lower()

    print(
        "OCR FILE:",
        file_path
    )

    print(
        "FILE TYPE:",
        extension
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
    # UNSUPPORTED FILE
    # ========================================================

    print(
        "UNSUPPORTED FILE TYPE:",
        extension
    )

    return ""