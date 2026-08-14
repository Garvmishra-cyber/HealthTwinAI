from modules.ocr import extract_text

text = extract_text("uploads/Screenshot 2026-08-14 012525.png")

print("\n===== OCR RESULT =====\n")
print(text)
print("\n======================\n")