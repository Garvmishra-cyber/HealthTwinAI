from modules.ocr import extract_text
from modules.analyzer import analyze_report


# =========================================================
# TEST MEDICAL REPORT
# =========================================================

PDF_PATH = r"uploads\243c4a9f-d595-4d32-b211-d2c87a0dc368.pdf"


print("\n")
print("=" * 70)
print("        HEALTH TWIN AI - FULL REPORT ANALYZER TEST")
print("=" * 70)


# =========================================================
# STEP 1 - OCR
# =========================================================

print("\n[1/2] Extracting text from medical report...\n")

text = extract_text(PDF_PATH)


if not text:

    print("❌ OCR returned no text.")

    print("\nCheck the PDF path or OCR configuration.")

    raise SystemExit


print("✅ OCR successful.")

print("\n")
print("-" * 70)
print("OCR TEXT")
print("-" * 70)

print(text)

print("-" * 70)


# =========================================================
# STEP 2 - ANALYSIS
# =========================================================

print("\n[2/2] Analyzing medical report...\n")

result = analyze_report(text)


# =========================================================
# PARAMETERS
# =========================================================

print("=" * 70)
print("HEALTH PARAMETERS")
print("=" * 70)

for name, value in result["parameters"].items():

    print(f"{name}: {value}")


# =========================================================
# FINDINGS
# =========================================================

print("\n")
print("=" * 70)
print("FINDINGS")
print("=" * 70)

for finding in result["findings"]:

    print("•", finding)


# =========================================================
# RECOMMENDATIONS
# =========================================================

print("\n")
print("=" * 70)
print("RECOMMENDATIONS")
print("=" * 70)

for recommendation in result["recommendations"]:

    print("•", recommendation)


# =========================================================
# SCORE
# =========================================================

print("\n")
print("=" * 70)
print("HEALTH SCORE")
print("=" * 70)

print(
    f"Score: {result['score']}/100"
)


# =========================================================
# RISK
# =========================================================

print("\n")
print("=" * 70)
print("RISK LEVEL")
print("=" * 70)

print(
    result["risk"]
)


# =========================================================
# COMPLETE
# =========================================================

print("\n")
print("=" * 70)
print("            ANALYSIS TEST COMPLETE")
print("=" * 70)
print("\n")