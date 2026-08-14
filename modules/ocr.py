import pytesseract
from PIL import Image, ImageOps, ImageFilter
from pdf2image import convert_from_path


# ============================================================
# TESSERACT PATH
# ============================================================

pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)


# ============================================================
# IMAGE PREPROCESSING
# ============================================================

def preprocess_image(image):

    # Grayscale only
    # Extra contrast enhancement is avoided because
    # it can change small digits such as 9 -> 8.
    image = ImageOps.grayscale(image)

    # Sharpen slightly
    image = image.filter(
        ImageFilter.SHARPEN
    )

    # Resize 3x
    width, height = image.size

    image = image.resize(
        (width * 3, height * 3)
    )

    return image


# ============================================================
# NORMAL OCR
# ============================================================

def run_ocr(image):

    config = (
        "--oem 3 "
        "--psm 6 "
        "-c preserve_interword_spaces=1"
    )

    return pytesseract.image_to_string(
        image,
        config=config
    )


# ============================================================
# MAIN OCR
# ============================================================

def extract_text(file_path):

    text = ""

    # ========================================================
    # PDF
    # ========================================================

    if file_path.lower().endswith(".pdf"):

        pages = convert_from_path(
            file_path,
            dpi=300
        )

        for page_number, page in enumerate(
            pages,
            start=1
        ):

            processed_page = preprocess_image(
                page
            )

            page_text = run_ocr(
                processed_page
            )

            text += (
                f"\n\n===== PAGE {page_number} =====\n\n"
            )

            text += page_text

    # ========================================================
    # IMAGE
    # ========================================================

    else:

        image = Image.open(
            file_path
        )

        processed_image = preprocess_image(
            image
        )

        text = run_ocr(
            processed_image
        )

    return text