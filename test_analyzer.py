from modules.ocr import extract_text
from modules.analyzer import analyze_report


image_path = "uploads/Screenshot 2026-08-14 012525.png"


print("\n========================================")
print("              OCR TEST")
print("========================================")

text = extract_text(image_path)

print(text)


print("\n========================================")
print("           ANALYZER TEST")
print("========================================")

report = analyze_report(text)


print("\nHEALTH PARAMETERS")
print("----------------------------------------")

for key, value in report["parameters"].items():
    print(f"{key}: {value}")


print("\nFINDINGS")
print("----------------------------------------")

for item in report["findings"]:
    print(item)


print("\nRECOMMENDATIONS")
print("----------------------------------------")

for item in report["recommendations"]:
    print(item)


print("\nHEALTH SCORE")
print("----------------------------------------")

print(report["score"], "/100")


print("\nRISK LEVEL")
print("----------------------------------------")

print(report["risk"])


print("\n========================================")
print("              TEST COMPLETE")
print("========================================")