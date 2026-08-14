import re


def get_number_after_label(text, label_pattern):
    """
    Finds the first number appearing after a given label.
    """

    match = re.search(
        label_pattern + r".{0,80}?(\d+(?:\.\d+)?)",
        text,
        re.IGNORECASE | re.DOTALL
    )

    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None

    return None


def analyze_report(text):

    findings = []
    recommendations = []
    parameters = {}

    score = 100

    # ---------------------------------------------------------
    # Normalize OCR text
    # ---------------------------------------------------------

    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)

    print("\n========== ANALYZER INPUT ==========")
    print(text)
    print("====================================\n")

    # =========================================================
    # HEMOGLOBIN
    # =========================================================

    hb = get_number_after_label(
        text,
        r"hemoglobin(?:\s*\(hb\))?"
    )

    if hb is not None:

        parameters["Hemoglobin"] = f"{hb:g} g/dL"

        if hb < 13:

            findings.append(
                f"⚠ Hemoglobin below reference range ({hb:g} g/dL)"
            )

            recommendations.append(
                "Discuss the hemoglobin result with a qualified healthcare professional."
            )

            score -= 15

        else:

            findings.append(
                f"✅ Hemoglobin normal ({hb:g} g/dL)"
            )

    # =========================================================
    # RBC
    # =========================================================

    rbc = get_number_after_label(
        text,
        r"(?:total\s+)?rbc\s+count"
    )

    if rbc is not None:

        parameters["RBC"] = f"{rbc:g}"

        if rbc < 4.5:

            findings.append(
                f"⚠ RBC count below reference range ({rbc:g})"
            )

            score -= 10

        else:

            findings.append(
                f"✅ RBC count normal ({rbc:g})"
            )

    # =========================================================
    # WBC
    #
    # OCR may read:
    #
    # WBC COUNT
    # WEC COUNT
    # WBC count
    # WEC count
    # Total WEC count
    # Total WBC count
    # =========================================================

    wbc = get_number_after_label(
        text,
        r"(?:total\s+)?w(?:bc|ec)\s+count"
    )

    if wbc is not None:

        parameters["WBC"] = f"{int(wbc)}/µL"

        if wbc < 4000:

            findings.append(
                f"⚠ WBC count below reference range ({int(wbc)}/µL)"
            )

            recommendations.append(
                "Discuss the WBC result with a qualified healthcare professional."
            )

            score -= 10

        elif wbc > 11000:

            findings.append(
                f"⚠ WBC count above reference range ({int(wbc)}/µL)"
            )

            recommendations.append(
                "Discuss the WBC result with a qualified healthcare professional."
            )

            score -= 15

        else:

            findings.append(
                f"✅ WBC count normal ({int(wbc)}/µL)"
            )

    # =========================================================
    # PLATELETS
    # =========================================================

    platelets = get_number_after_label(
        text,
        r"platelet\s+count"
    )

    if platelets is not None:

        parameters["Platelets"] = f"{int(platelets)}/µL"

        if platelets < 150000:

            findings.append(
                f"⚠ Platelet count below reference range ({int(platelets)}/µL)"
            )

            score -= 15

        elif platelets > 450000:

            findings.append(
                f"⚠ Platelet count above reference range ({int(platelets)}/µL)"
            )

            score -= 10

        else:

            findings.append(
                f"✅ Platelet count normal ({int(platelets)}/µL)"
            )

    # =========================================================
    # SCORE
    # =========================================================

    score = max(0, min(100, score))

    # =========================================================
    # RISK
    # =========================================================

    if score >= 90:

        risk = "🟢 Low Risk"

    elif score >= 70:

        risk = "🟡 Medium Risk"

    else:

        risk = "🔴 High Risk"

    # =========================================================
    # DEFAULTS
    # =========================================================

    if not findings:

        findings.append(
            "ℹ No supported health parameters detected."
        )

    if not recommendations:

        recommendations.append(
            "Continue maintaining healthy habits and follow your healthcare professional's advice."
        )

    # =========================================================
    # FINAL RESULT
    # =========================================================

    return {
        "parameters": parameters,
        "findings": findings,
        "recommendations": recommendations,
        "score": score,
        "risk": risk
    }