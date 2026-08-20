import re


# =========================================================
# CLEAN TEXT
# =========================================================

def clean_text(text):

    if not text:
        return ""

    text = str(text)

    # Common OCR corrections
    replacements = {
        "haemoglobin": "hemoglobin",
        "HEMOGLOBIN": "hemoglobin",
        "WEC": "WBC",
        "WeC": "WBC",
        "wbc count": "wbc count",
        "R.B.C": "RBC",
        "R.B.C.": "RBC",
        "RBCs": "RBC",
        "PLT": "platelet",
        "Plt": "platelet",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    # Newlines -> spaces
    text = text.replace("\n", " ")

    # Multiple spaces
    text = re.sub(r"\s+", " ", text)

    return text.strip()


# =========================================================
# NUMBER CLEANER
# =========================================================

def parse_number(value):

    if value is None:
        return None

    value = str(value)

    # Remove commas
    value = value.replace(",", "")

    match = re.search(
        r"\d+(?:\.\d+)?",
        value
    )

    if not match:
        return None

    try:
        return float(match.group())
    except ValueError:
        return None


# =========================================================
# FIND NUMBER AFTER LABEL
# =========================================================

def get_number_after_label(
    text,
    label_pattern,
    max_chars=100
):

    pattern = (
        label_pattern
        + rf".{{0,{max_chars}}}?"
        + r"(\d+(?:,\d+)*(?:\.\d+)?)"
    )

    match = re.search(
        pattern,
        text,
        re.IGNORECASE | re.DOTALL
    )

    if not match:
        return None

    return parse_number(
        match.group(1)
    )


# =========================================================
# FIND PARAMETER
# =========================================================

def find_parameter(
    text,
    patterns
):

    for pattern in patterns:

        value = get_number_after_label(
            text,
            pattern
        )

        if value is not None:
            return value

    return None


# =========================================================
# ANALYZE REPORT
# =========================================================

def analyze_report(text):

    findings = []

    recommendations = []

    parameters = {}

    score = 100

    # -----------------------------------------------------
    # CLEAN OCR TEXT
    # -----------------------------------------------------

    text = clean_text(text)

    print(
        "\n========== ANALYZER INPUT =========="
    )

    print(text)

    print(
        "====================================\n"
    )

    # =====================================================
    # HEMOGLOBIN
    # =====================================================

    hb = find_parameter(
        text,
        [

            r"hemoglobin\s*(?:\(hb\))?",

            r"hemoglobin\s*hb",

            r"\bhb\b"

        ]
    )

    if hb is not None:

        parameters["Hemoglobin"] = (
            f"{hb:g} g/dL"
        )

        if hb < 13:

            findings.append(
                f"⚠ Hemoglobin below reference "
                f"range ({hb:g} g/dL)"
            )

            recommendations.append(
                "Discuss the hemoglobin result "
                "with a qualified healthcare professional."
            )

            score -= 15

        else:

            findings.append(
                f"✅ Hemoglobin normal "
                f"({hb:g} g/dL)"
            )

    # =====================================================
    # RBC
    # =====================================================

    rbc = find_parameter(
        text,
        [

            r"(?:total\s*)?rbc\s*(?:count)?",

            r"red\s+blood\s+cell\s*(?:count)?",

            r"red\s+cell\s*(?:count)?",

            r"r\.?\s*b\.?\s*c\.?"

        ]
    )

    if rbc is not None:

        # RBC is generally reported as millions/µL.
        parameters["RBC"] = (
            f"{rbc:g}"
        )

        if rbc < 4.5:

            findings.append(
                f"⚠ RBC count below reference "
                f"range ({rbc:g})"
            )

            recommendations.append(
                "Discuss the RBC result with "
                "a qualified healthcare professional."
            )

            score -= 10

        elif rbc > 6.0:

            findings.append(
                f"⚠ RBC count above reference "
                f"range ({rbc:g})"
            )

            recommendations.append(
                "Discuss the RBC result with "
                "a qualified healthcare professional."
            )

            score -= 10

        else:

            findings.append(
                f"✅ RBC count within the "
                f"supported range ({rbc:g})"
            )

    # =====================================================
    # WBC
    # =====================================================

    wbc = find_parameter(
        text,
        [

            r"(?:total\s*)?wbc\s*(?:count)?",

            r"(?:total\s*)?wec\s*(?:count)?",

            r"white\s+blood\s+cell\s*(?:count)?",

            r"white\s+cell\s*(?:count)?",

            r"w\.?\s*b\.?\s*c\.?"

        ]
    )

    if wbc is not None:

        # -------------------------------------------------
        # Handle values such as:
        #
        # 7.2 x10^3/uL
        # 7.2 10^3/uL
        # 7200 /uL
        # -------------------------------------------------

        after_wbc = re.search(

            r"(?:wbc|wec|white\s+blood\s+cell|"
            r"white\s+cell)"
            r".{0,100}?"
            r"(\d+(?:\.\d+)?)"
            r"\s*(?:x|×)?\s*10\s*[\^]?\s*3",

            text,

            re.IGNORECASE
            | re.DOTALL

        )

        if after_wbc:

            wbc_value = (
                float(
                    after_wbc.group(1)
                )
                * 1000
            )

        else:

            wbc_value = wbc

            # If OCR captured a decimal WBC
            # such as 7.2, treat it as 7200.
            if (
                wbc_value < 100
            ):

                wbc_value *= 1000

        wbc_value = int(
            round(wbc_value)
        )

        parameters["WBC"] = (
            f"{wbc_value}/µL"
        )

        # -------------------------------------------------
        # WBC RANGE
        # -------------------------------------------------

        if wbc_value < 4000:

            findings.append(
                f"⚠ WBC count below reference "
                f"range ({wbc_value}/µL)"
            )

            recommendations.append(
                "Discuss the WBC result with "
                "a qualified healthcare professional."
            )

            score -= 10

        elif wbc_value > 11000:

            findings.append(
                f"⚠ WBC count above reference "
                f"range ({wbc_value}/µL)"
            )

            recommendations.append(
                "Discuss the WBC result with "
                "a qualified healthcare professional."
            )

            score -= 15

        else:

            findings.append(
                f"✅ WBC count within the "
                f"supported range ({wbc_value}/µL)"
            )

    # =====================================================
    # PLATELETS
    # =====================================================

    platelets = find_parameter(
        text,
        [

            r"platelet\s*(?:count)?",

            r"platelets\s*(?:count)?",

            r"plt\s*(?:count)?",

            r"platelet\s+count"

        ]
    )

    if platelets is not None:

        # -------------------------------------------------
        # Detect x10^3 / µL notation
        #
        # Example:
        # Platelet Count 275 x10^3/uL
        #
        # Convert:
        # 275 -> 275000 /µL
        # -------------------------------------------------

        platelet_thousands = re.search(

            r"(?:platelet|platelets|plt)"
            r".{0,100}?"
            r"(\d+(?:\.\d+)?)"
            r"\s*(?:x|×)?\s*10\s*[\^]?\s*3",

            text,

            re.IGNORECASE
            | re.DOTALL

        )

        if platelet_thousands:

            platelet_value = (

                float(
                    platelet_thousands.group(1)
                )
                * 1000

            )

        else:

            platelet_value = platelets

            # -------------------------------------------------
            # Many reports use 150-450 x10^3/µL.
            # If OCR gives a value such as 275,
            # treat it as 275000/µL.
            # -------------------------------------------------

            if (
                100 <= platelet_value <= 1000
            ):

                platelet_value *= 1000

        platelet_value = int(
            round(platelet_value)
        )

        parameters["Platelets"] = (
            f"{platelet_value}/µL"
        )

        # -------------------------------------------------
        # PLATELET RANGE
        # -------------------------------------------------

        if platelet_value < 150000:

            findings.append(
                f"⚠ Platelet count below "
                f"reference range "
                f"({platelet_value}/µL)"
            )

            recommendations.append(
                "Discuss the platelet result "
                "with a qualified healthcare professional."
            )

            score -= 15

        elif platelet_value > 450000:

            findings.append(
                f"⚠ Platelet count above "
                f"reference range "
                f"({platelet_value}/µL)"
            )

            recommendations.append(
                "Discuss the platelet result "
                "with a qualified healthcare professional."
            )

            score -= 10

        else:

            findings.append(
                f"✅ Platelet count within the "
                f"supported range "
                f"({platelet_value}/µL)"
            )

    # =====================================================
    # SCORE
    # =====================================================

    score = max(
        0,
        min(
            100,
            score
        )
    )

    # =====================================================
    # RISK
    # =====================================================

    if score >= 90:

        risk = "🟢 Low Risk"

    elif score >= 70:

        risk = "🟡 Medium Risk"

    else:

        risk = "🔴 High Risk"

    # =====================================================
    # DEFAULT FINDINGS
    # =====================================================

    if not findings:

        findings.append(
            "ℹ No supported health parameters "
            "were detected from the report."
        )

    # =====================================================
    # DEFAULT RECOMMENDATION
    # =====================================================

    if not recommendations:

        recommendations.append(
            "Continue maintaining healthy habits "
            "and follow your healthcare professional's advice."
        )

    # =====================================================
    # FINAL RESULT
    # =====================================================

    result = {

        "parameters":
            parameters,

        "findings":
            findings,

        "recommendations":
            recommendations,

        "score":
            score,

        "risk":
            risk

    }

    print(
        "\n========== ANALYZER RESULT =========="
    )

    print(result)

    print(
        "=====================================\n"
    )

    return result