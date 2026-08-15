import re


# ============================================================
# HEALTH REPORT ANALYZER
# ============================================================
# IMPORTANT:
# This module performs screening/flagging from laboratory
# report text. It does NOT diagnose diseases.
# ============================================================


# ============================================================
# TEXT NORMALIZATION
# ============================================================

def normalize_text(text):

    if not text:
        return ""

    text = str(text)

    # Normalize common OCR characters
    replacements = {
        "µ": "u",
        "μ": "u",
        "–": "-",
        "—": "-",
        "−": "-",
        "|": " ",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    # Preserve line structure because laboratory reports
    # often place label and value on separate lines.
    lines = []

    for line in text.splitlines():

        line = re.sub(
            r"[ \t]+",
            " ",
            line
        ).strip()

        if line:
            lines.append(line)

    return "\n".join(lines)


def compact_text(text):

    text = normalize_text(text)

    return re.sub(
        r"\s+",
        " ",
        text
    ).strip()


# ============================================================
# NUMBER HELPERS
# ============================================================

def clean_number(value):

    if value is None:
        return None

    value = str(value).strip()

    # Remove commas used in values such as 275,000
    value = value.replace(",", "")

    try:
        return float(value)
    except ValueError:
        return None


def format_number(value):

    if value is None:
        return ""

    if float(value).is_integer():
        return str(int(value))

    return f"{value:g}"


# ============================================================
# SAFE LAB VALUE EXTRACTION
# ============================================================

def get_value_with_unit(
    text,
    label_pattern,
    unit_pattern,
    max_chars=80
):
    """
    Extracts a value only when the expected unit is nearby.

    This is intentionally stricter than simply searching for
    the first number after a label.

    Example:
        Hemoglobin
        10.4
        g/dL

    will match.

    MCH
    30.1
    pg

    will NOT be treated as Hemoglobin.
    """

    pattern = (
        label_pattern
        + rf"[^0-9]{{0,{max_chars}}}"
        + r"(\d+(?:\.\d+)?)"
        + r"\s*"
        + unit_pattern
    )

    match = re.search(
        pattern,
        text,
        re.IGNORECASE | re.DOTALL
    )

    if not match:
        return None

    return clean_number(
        match.group(1)
    )


def get_number_after_label(
    text,
    label_pattern,
    max_chars=80
):
    """
    Fallback numeric extraction.

    Use only for tests where the report does not reliably
    provide a unit.
    """

    pattern = (
        label_pattern
        + rf"[^0-9]{{0,{max_chars}}}"
        + r"(\d+(?:\.\d+)?)"
    )

    match = re.search(
        pattern,
        text,
        re.IGNORECASE | re.DOTALL
    )

    if not match:
        return None

    return clean_number(
        match.group(1)
    )


# ============================================================
# ADD PARAMETER
# ============================================================

def add_parameter(
    parameters,
    name,
    value,
    unit=""
):

    if value is None:
        return

    value_text = format_number(value)

    if unit:
        parameters[name] = (
            f"{value_text} {unit}"
        )
    else:
        parameters[name] = value_text


# ============================================================
# FINDING / RECOMMENDATION HELPERS
# ============================================================

def add_finding(
    findings,
    recommendations,
    message,
    recommendation=None
):

    findings.append(message)

    if recommendation:

        if recommendation not in recommendations:

            recommendations.append(
                recommendation
            )


# ============================================================
# ANALYZE REPORT
# ============================================================

def analyze_report(text):

    findings = []

    recommendations = []

    parameters = {}

    score = 100

    # --------------------------------------------------------
    # NORMALIZE
    # --------------------------------------------------------

    text = normalize_text(text)

    compact = compact_text(text)

    print(
        "\n========== ANALYZER INPUT =========="
    )

    print(text)

    print(
        "====================================\n"
    )

    # ========================================================
    # CBC
    # ========================================================

    # --------------------------------------------------------
    # HEMOGLOBIN
    # --------------------------------------------------------
    # IMPORTANT:
    # Must require g/dL so MCH 30.1 pg is not detected as Hb.
    # --------------------------------------------------------

    hb = get_value_with_unit(
        text,
        r"(?<!mean corp. )"
        r"(?<!mean corpuscular )"
        r"\b(?:hemoglobin|haemoglobin)\b"
        r"(?!\s*\(?\s*MCHC?\s*\)?)",
        r"g\s*/?\s*d[lI1]"
    )

    if hb is not None:

        add_parameter(
            parameters,
            "Hemoglobin",
            hb,
            "g/dL"
        )

        if hb < 13:

            add_finding(
                findings,
                recommendations,
                (
                    f"⚠ Hemoglobin appears below the "
                    f"configured screening range "
                    f"({format_number(hb)} g/dL)."
                ),
                (
                    "Discuss the hemoglobin result with "
                    "a qualified healthcare professional."
                )
            )

            score -= 15

        elif hb > 20:

            add_finding(
                findings,
                recommendations,
                (
                    f"⚠ Hemoglobin value should be verified "
                    f"({format_number(hb)} g/dL)."
                ),
                (
                    "Verify the hemoglobin value and unit "
                    "against the original laboratory report."
                )
            )

            score -= 5

        else:

            findings.append(
                (
                    f"✅ Hemoglobin appears within the "
                    f"configured screening range "
                    f"({format_number(hb)} g/dL)."
                )
            )

    # --------------------------------------------------------
    # RBC
    # --------------------------------------------------------

    rbc = get_value_with_unit(
        text,
        r"\b(?:total\s+)?RBC(?:\s+count)?\b",
        r"(?:million/?uL|10\^?12/?L|x10\^?12/?L)?"
    )

    if rbc is None:

        rbc = get_number_after_label(
            text,
            r"\b(?:total\s+)?RBC\s+count\b"
        )

    if rbc is not None:

        add_parameter(
            parameters,
            "RBC",
            rbc
        )

        if rbc < 4.0:

            add_finding(
                findings,
                recommendations,
                (
                    f"⚠ RBC count appears low "
                    f"({format_number(rbc)})."
                ),
                (
                    "Discuss the RBC result with a "
                    "qualified healthcare professional."
                )
            )

            score -= 10

        elif rbc > 6.0:

            add_finding(
                findings,
                recommendations,
                (
                    f"⚠ RBC count appears high "
                    f"({format_number(rbc)})."
                ),
                (
                    "Discuss the RBC result with a "
                    "qualified healthcare professional."
                )
            )

            score -= 10

        else:

            findings.append(
                (
                    f"✅ RBC count is within the "
                    f"configured screening range "
                    f"({format_number(rbc)})."
                )
            )

    # --------------------------------------------------------
    # WBC
    # --------------------------------------------------------

    wbc = get_value_with_unit(
        text,
        r"\b(?:total\s+)?W(?:BC|EC)\s+count\b",
        r"(?:/uL|/ul|cells/?uL|cells/?ul)"
    )

    if wbc is None:

        wbc = get_number_after_label(
            text,
            r"\b(?:total\s+)?W(?:BC|EC)\s+count\b"
        )

        # Prevent obvious OCR garbage.
        if wbc is not None and wbc < 100:
            wbc = None

    if wbc is not None:

        add_parameter(
            parameters,
            "WBC",
            wbc,
            "/uL"
        )

        if wbc < 4000:

            add_finding(
                findings,
                recommendations,
                (
                    f"⚠ WBC count appears low "
                    f"({format_number(wbc)}/uL)."
                ),
                (
                    "Discuss the WBC result with a "
                    "qualified healthcare professional."
                )
            )

            score -= 10

        elif wbc > 11000:

            add_finding(
                findings,
                recommendations,
                (
                    f"⚠ WBC count appears high "
                    f"({format_number(wbc)}/uL)."
                ),
                (
                    "Discuss the WBC result with a "
                    "qualified healthcare professional."
                )
            )

            score -= 10

        else:

            findings.append(
                (
                    f"✅ WBC count is within the "
                    f"configured screening range "
                    f"({format_number(wbc)}/uL)."
                )
            )

    # --------------------------------------------------------
    # PLATELETS
    # --------------------------------------------------------

    platelets = get_value_with_unit(
        text,
        r"\bplatelet\s+count\b",
        r"(?:/uL|/ul|cells/?uL|cells/?ul)"
    )

    if platelets is None:

        platelets = get_number_after_label(
            text,
            r"\bplatelet\s+count\b"
        )

        # Many reports give platelet values like 275000.
        if platelets is not None and platelets < 1000:

            platelets = None

    if platelets is not None:

        add_parameter(
            parameters,
            "Platelets",
            platelets,
            "/uL"
        )

        if platelets < 150000:

            add_finding(
                findings,
                recommendations,
                (
                    f"⚠ Platelet count appears low "
                    f"({format_number(platelets)}/uL)."
                ),
                (
                    "Discuss the platelet result with a "
                    "qualified healthcare professional."
                )
            )

            score -= 15

        elif platelets > 450000:

            add_finding(
                findings,
                recommendations,
                (
                    f"⚠ Platelet count appears high "
                    f"({format_number(platelets)}/uL)."
                ),
                (
                    "Discuss the platelet result with a "
                    "qualified healthcare professional."
                )
            )

            score -= 10

        else:

            findings.append(
                (
                    f"✅ Platelet count is within the "
                    f"configured screening range "
                    f"({format_number(platelets)}/uL)."
                )
            )

    # ========================================================
    # RED CELL INDICES
    # ========================================================

    # --------------------------------------------------------
    # HEMATOCRIT / PCV
    # --------------------------------------------------------
    # OCR-safe extraction: many scanned reports lose the % symbol.
    # Example: Packed Cell Volume (PCV) 57.5 High 40-50 3
    # In that case, use the first number immediately after the label.

    hct_label_pattern = (
        r"\b(?:"
        r"hematocrit"
        r"|haematocrit"
        r"|PCV"
        r"|packed\s+cell\s+volume"
        r")\b"
    )

    hct = get_value_with_unit(
        text,
        hct_label_pattern,
        r"%"
    )

    # Fallback when OCR has lost the % symbol.
    if hct is None:
        hct = get_number_after_label(
            text,
            hct_label_pattern,
            max_chars=60
        )

    # Reject obviously impossible OCR values.
    if hct is not None and (hct < 10 or hct > 80):
        hct = None

    if hct is not None:

        add_parameter(
            parameters,
            "Hematocrit",
            hct,
            "%"
        )

        if hct < 36:

            add_finding(
                findings,
                recommendations,
                (
                    f"⚠ Hematocrit/PCV appears low "
                    f"({format_number(hct)}%)."
                ),
                (
                    "Discuss the hematocrit/PCV result with "
                    "a qualified healthcare professional."
                )
            )

            score -= 8

        elif hct > 54:

            add_finding(
                findings,
                recommendations,
                (
                    f"⚠ Hematocrit/PCV appears high "
                    f"({format_number(hct)}%)."
                ),
                (
                    "Discuss the hematocrit/PCV result with "
                    "a qualified healthcare professional."
                )
            )

            score -= 8

        else:

            findings.append(
                (
                    f"✅ Hematocrit/PCV appears within the "
                    f"configured screening range "
                    f"({format_number(hct)}%)."
                )
            )

    # --------------------------------------------------------
    # MCV
    # --------------------------------------------------------

    mcv = get_value_with_unit(
        text,
        r"\bMCV\b",
        r"fL"
    )

    if mcv is not None:

        add_parameter(
            parameters,
            "MCV",
            mcv,
            "fL"
        )

        if mcv < 80:

            findings.append(
                (
                    f"⚠ MCV appears low "
                    f"({format_number(mcv)} fL)."
                )
            )

        elif mcv > 100:

            findings.append(
                (
                    f"⚠ MCV appears high "
                    f"({format_number(mcv)} fL)."
                )
            )

    # --------------------------------------------------------
    # MCH
    # --------------------------------------------------------

    mch = get_value_with_unit(
        text,
        r"\bMCH\b",
        r"pg"
    )

    if mch is not None:

        add_parameter(
            parameters,
            "MCH",
            mch,
            "pg"
        )

        if mch < 27 or mch > 33:

            findings.append(
                (
                    f"⚠ MCH is outside the configured "
                    f"screening range ({format_number(mch)} pg)."
                )
            )

    # --------------------------------------------------------
    # MCHC
    # --------------------------------------------------------

    mchc = get_value_with_unit(
        text,
        r"\bMCHC\b",
        r"g\s*/?\s*d[lI1]"
    )

    if mchc is not None:

        add_parameter(
            parameters,
            "MCHC",
            mchc,
            "g/dL"
        )

        if mchc < 32 or mchc > 36:

            findings.append(
                (
                    f"⚠ MCHC is outside the configured "
                    f"screening range ({format_number(mchc)} g/dL)."
                )
            )

    # --------------------------------------------------------
    # RDW
    # --------------------------------------------------------

    rdw = get_value_with_unit(
        text,
        r"\bRDW(?:-CV)?\b",
        r"%"
    )

    if rdw is not None:

        add_parameter(
            parameters,
            "RDW",
            rdw,
            "%"
        )

    # ========================================================
    # INFLAMMATION
    # ========================================================

    # --------------------------------------------------------
    # ESR
    # --------------------------------------------------------

    esr = get_value_with_unit(
        text,
        r"\b(?:ESR|erythrocyte\s+sedimentation\s+rate)\b",
        r"mm\s*/?\s*hr"
    )

    if esr is None:

        esr = get_number_after_label(
            text,
            r"\b(?:ESR|erythrocyte\s+sedimentation\s+rate)\b"
        )

        # Reject impossible OCR values.
        if esr is not None and esr > 200:
            esr = None

    if esr is not None:

        add_parameter(
            parameters,
            "ESR",
            esr,
            "mm/hr"
        )

        if esr > 20:

            add_finding(
                findings,
                recommendations,
                (
                    f"⚠ ESR appears elevated "
                    f"({format_number(esr)} mm/hr)."
                ),
                (
                    "ESR is nonspecific and should be "
                    "interpreted with other clinical findings."
                )
            )

            score -= 5

    # --------------------------------------------------------
    # CRP
    # --------------------------------------------------------

    crp = get_value_with_unit(
        text,
        r"\b(?:CRP|C-reactive\s+protein)\b",
        r"(?:mg\s*/?\s*L|mg\s*/?\s*dL)"
    )

    if crp is None:

        crp = get_number_after_label(
            text,
            r"\b(?:CRP|C-reactive\s+protein)\b"
        )

    if crp is not None:

        add_parameter(
            parameters,
            "CRP",
            crp
        )

        if crp > 5:

            add_finding(
                findings,
                recommendations,
                (
                    f"⚠ CRP appears elevated "
                    f"({format_number(crp)})."
                ),
                (
                    "CRP elevation is nonspecific and can "
                    "occur with inflammation or infection; "
                    "clinical interpretation is recommended."
                )
            )

            score -= 5

    # ========================================================
    # GLUCOSE
    # ========================================================

    glucose = get_value_with_unit(
        text,
        r"\b(?:blood\s+)?glucose\b",
        r"mg\s*/?\s*dL"
    )

    if glucose is None:

        glucose = get_number_after_label(
            text,
            r"\b(?:blood\s+)?glucose\b"
        )

    # Reject obviously impossible OCR values.
    if glucose is not None and glucose > 1000:

        glucose = None

    if glucose is not None:

        add_parameter(
            parameters,
            "Glucose",
            glucose,
            "mg/dL"
        )

        if glucose >= 126:

            add_finding(
                findings,
                recommendations,
                (
                    f"⚠ Glucose is elevated "
                    f"({format_number(glucose)} mg/dL)."
                ),
                (
                    "Discuss the glucose result with a "
                    "qualified healthcare professional."
                )
            )

            score -= 15

        elif glucose < 70:

            add_finding(
                findings,
                recommendations,
                (
                    f"⚠ Glucose appears low "
                    f"({format_number(glucose)} mg/dL)."
                ),
                (
                    "Discuss the glucose result with a "
                    "qualified healthcare professional."
                )
            )

            score -= 10

    # ========================================================
    # LIPID PROFILE
    # ========================================================

    # --------------------------------------------------------
    # TOTAL CHOLESTEROL
    # --------------------------------------------------------

    cholesterol = get_value_with_unit(
        text,
        r"\b(?:total\s+)?cholesterol\b",
        r"mg\s*/?\s*dL"
    )

    if cholesterol is not None:

        add_parameter(
            parameters,
            "Total Cholesterol",
            cholesterol,
            "mg/dL"
        )

        if cholesterol >= 200:

            findings.append(
                (
                    f"⚠ Total cholesterol appears high "
                    f"({format_number(cholesterol)} mg/dL)."
                )
            )

    # --------------------------------------------------------
    # TRIGLYCERIDES
    # --------------------------------------------------------

    triglycerides = get_value_with_unit(
        text,
        r"\btriglycerides?\b",
        r"mg\s*/?\s*dL"
    )

    if triglycerides is not None:

        add_parameter(
            parameters,
            "Triglycerides",
            triglycerides,
            "mg/dL"
        )

        if triglycerides >= 150:

            findings.append(
                (
                    f"⚠ Triglycerides appear high "
                    f"({format_number(triglycerides)} mg/dL)."
                )
            )

    # --------------------------------------------------------
    # HDL
    # --------------------------------------------------------

    hdl = get_value_with_unit(
        text,
        r"\bHDL(?:-C)?\b",
        r"mg\s*/?\s*dL"
    )

    if hdl is not None:

        add_parameter(
            parameters,
            "HDL",
            hdl,
            "mg/dL"
        )

        if hdl < 40:

            findings.append(
                (
                    f"⚠ HDL appears low "
                    f"({format_number(hdl)} mg/dL)."
                )
            )

    # --------------------------------------------------------
    # LDL
    # --------------------------------------------------------

    ldl = get_value_with_unit(
        text,
        r"\bLDL(?:-C)?\b",
        r"mg\s*/?\s*dL"
    )

    if ldl is not None:

        add_parameter(
            parameters,
            "LDL",
            ldl,
            "mg/dL"
        )

        if ldl >= 130:

            findings.append(
                (
                    f"⚠ LDL appears high "
                    f"({format_number(ldl)} mg/dL)."
                )
            )

    # ========================================================
    # KIDNEY / ELECTROLYTES
    # ========================================================

    # --------------------------------------------------------
    # SODIUM
    # --------------------------------------------------------

    sodium = get_value_with_unit(
        text,
        r"\b(?:serum\s+)?sodium\b",
        r"mmol\s*/?\s*L"
    )

    if sodium is not None:

        add_parameter(
            parameters,
            "Sodium",
            sodium,
            "mmol/L"
        )

        if sodium < 135 or sodium > 145:

            findings.append(
                (
                    f"⚠ Sodium is outside the configured "
                    f"screening range ({format_number(sodium)} mmol/L)."
                )
            )

    # --------------------------------------------------------
    # POTASSIUM
    # --------------------------------------------------------

    potassium = get_value_with_unit(
        text,
        r"\b(?:serum\s+)?potassium\b",
        r"mmol\s*/?\s*L"
    )

    if potassium is not None:

        add_parameter(
            parameters,
            "Potassium",
            potassium,
            "mmol/L"
        )

        if potassium < 3.5 or potassium > 5.2:

            findings.append(
                (
                    f"⚠ Potassium is outside the configured "
                    f"screening range ({format_number(potassium)} mmol/L)."
                )
            )

    # --------------------------------------------------------
    # CREATININE
    # --------------------------------------------------------

    creatinine = get_value_with_unit(
        text,
        r"\bcreatinine\b",
        r"mg\s*/?\s*dL"
    )

    if creatinine is not None:

        add_parameter(
            parameters,
            "Creatinine",
            creatinine,
            "mg/dL"
        )

        if creatinine > 1.3:

            findings.append(
                (
                    f"⚠ Creatinine appears elevated "
                    f"({format_number(creatinine)} mg/dL)."
                )
            )

    # --------------------------------------------------------
    # UREA / BUN
    # --------------------------------------------------------

    urea = get_value_with_unit(
        text,
        r"\b(?:blood\s+)?urea\b",
        r"mg\s*/?\s*dL"
    )

    if urea is not None:

        add_parameter(
            parameters,
            "Urea",
            urea,
            "mg/dL"
        )

    bun = get_value_with_unit(
        text,
        r"\bBUN\b",
        r"mg\s*/?\s*dL"
    )

    if bun is not None:

        add_parameter(
            parameters,
            "BUN",
            bun,
            "mg/dL"
        )

    # ========================================================
    # LIVER
    # ========================================================

    # --------------------------------------------------------
    # AST / SGOT
    # --------------------------------------------------------

    ast = get_value_with_unit(
        text,
        r"\b(?:AST|SGOT)\b",
        r"(?:U\s*/?\s*L|IU\s*/?\s*L)"
    )

    if ast is None:

        ast = get_number_after_label(
            text,
            r"\b(?:AST|SGOT)\b"
        )

        if ast is not None and ast > 1000:
            ast = None

    if ast is not None:

        add_parameter(
            parameters,
            "AST/SGOT",
            ast,
            "U/L"
        )

        if ast > 40:

            findings.append(
                (
                    f"⚠ AST/SGOT appears elevated "
                    f"({format_number(ast)} U/L)."
                )
            )

    # --------------------------------------------------------
    # ALT / SGPT
    # --------------------------------------------------------

    alt = get_value_with_unit(
        text,
        r"\b(?:ALT|SGPT)\b",
        r"(?:U\s*/?\s*L|IU\s*/?\s*L)"
    )

    if alt is None:

        alt = get_number_after_label(
            text,
            r"\b(?:ALT|SGPT)\b"
        )

        if alt is not None and alt > 1000:
            alt = None

    if alt is not None:

        add_parameter(
            parameters,
            "ALT/SGPT",
            alt,
            "U/L"
        )

        if alt > 40:

            findings.append(
                (
                    f"⚠ ALT/SGPT appears elevated "
                    f"({format_number(alt)} U/L)."
                )
            )

    # --------------------------------------------------------
    # BILIRUBIN
    # --------------------------------------------------------

    bilirubin = get_value_with_unit(
        text,
        r"\btotal\s+bilirubin\b",
        r"mg\s*/?\s*dL"
    )

    if bilirubin is not None:

        add_parameter(
            parameters,
            "Total Bilirubin",
            bilirubin,
            "mg/dL"
        )

        if bilirubin > 1.2:

            findings.append(
                (
                    f"⚠ Total bilirubin appears elevated "
                    f"({format_number(bilirubin)} mg/dL)."
                )
            )

    # ========================================================
    # THYROID
    # ========================================================

    # --------------------------------------------------------
    # TSH
    # --------------------------------------------------------

    tsh = get_value_with_unit(
        text,
        r"\bTSH\b",
        r"(?:uIU\s*/?\s*mL|mIU\s*/?\s*L)"
    )

    if tsh is not None:

        add_parameter(
            parameters,
            "TSH",
            tsh,
            "mIU/L"
        )

    # --------------------------------------------------------
    # T3
    # --------------------------------------------------------

    t3 = get_value_with_unit(
        text,
        r"\bT3\b",
        r"(?:ng\s*/?\s*mL|ng\s*/?\s*dL)"
    )

    if t3 is not None:

        add_parameter(
            parameters,
            "T3",
            t3
        )

    # --------------------------------------------------------
    # T4
    # --------------------------------------------------------

    t4 = get_value_with_unit(
        text,
        r"\bT4\b",
        r"(?:ug\s*/?\s*dL|ng\s*/?\s*dL)"
    )

    if t4 is not None:

        add_parameter(
            parameters,
            "T4",
            t4
        )

    # ========================================================
    # EXPLICIT INFECTION / DISEASE TEST FLAGS
    # ========================================================
    #
    # IMPORTANT:
    # We ONLY flag a disease/test when the report text itself
    # explicitly indicates positive/detected/reactive/etc.
    #
    # We do NOT infer malaria/dengue/typhoid from CBC alone.
    # ========================================================

    def explicit_positive(
        patterns
    ):

        for pattern in patterns:

            match = re.search(
                pattern,
                compact,
                re.IGNORECASE
            )

            if match:

                # Look at a limited local context around match.
                start = max(
                    0,
                    match.start() - 30
                )

                end = min(
                    len(compact),
                    match.end() + 100
                )

                context = compact[
                    start:end
                ].lower()

                if re.search(
                    r"\b(?:positive|detected|reactive|"
                    r"present|found|confirmed)\b",
                    context
                ):

                    return True

        return False

    # --------------------------------------------------------
    # MALARIA
    # --------------------------------------------------------

    malaria_positive = explicit_positive([
        r"\bmalaria\b",
        r"\bmalaria\s+(?:antigen|parasite|test)\b",
        r"\bplasmodium\b"
    ])

    if malaria_positive:

        findings.append(
            (
                "⚠ A malaria-related test appears "
                "positive/detected in the report; "
                "clinical confirmation is required."
            )
        )

        recommendations.append(
            (
                "Discuss the malaria test result promptly "
                "with a qualified healthcare professional."
            )
        )

        score -= 20

    # --------------------------------------------------------
    # DENGUE
    # --------------------------------------------------------

    dengue_positive = explicit_positive([
        r"\bdengue\b",
        r"\bdengue\s+(?:NS1|IgM|IgG|antigen|test)\b"
    ])

    if dengue_positive:

        findings.append(
            (
                "⚠ A dengue-related test appears "
                "positive/detected in the report; "
                "clinical confirmation is required."
            )
        )

        recommendations.append(
            (
                "Discuss the dengue test result promptly "
                "with a qualified healthcare professional."
            )
        )

        score -= 20

    # --------------------------------------------------------
    # TYPHOID
    # --------------------------------------------------------

    typhoid_positive = explicit_positive([
        r"\btyphoid\b",
        r"\bwidal\b",
        r"\bsalmonella\b"
    ])

    if typhoid_positive:

        findings.append(
            (
                "⚠ A typhoid-related test appears "
                "positive/detected in the report; "
                "clinical confirmation is required."
            )
        )

        recommendations.append(
            (
                "Discuss the typhoid-related test result "
                "with a qualified healthcare professional."
            )
        )

        score -= 15

    # --------------------------------------------------------
    # HEPATITIS B
    # --------------------------------------------------------

    hepatitis_b_positive = explicit_positive([
        r"\bHBsAg\b",
        r"\bhepatitis\s+B\b"
    ])

    if hepatitis_b_positive:

        findings.append(
            (
                "⚠ A hepatitis B-related test appears "
                "positive/detected in the report."
            )
        )

        recommendations.append(
            (
                "Discuss this laboratory result with a "
                "qualified healthcare professional."
            )
        )

        score -= 20

    # --------------------------------------------------------
    # HEPATITIS C
    # --------------------------------------------------------

    hepatitis_c_positive = explicit_positive([
        r"\banti[-\s]?HCV\b",
        r"\bHCV\b",
        r"\bhepatitis\s+C\b"
    ])

    if hepatitis_c_positive:

        findings.append(
            (
                "⚠ A hepatitis C-related test appears "
                "positive/detected in the report."
            )
        )

        recommendations.append(
            (
                "Discuss this laboratory result with a "
                "qualified healthcare professional."
            )
        )

        score -= 20

    # ========================================================
    # URINE / KIDNEY / STONE-RELATED SCREENING
    # ========================================================

    urine_keywords = [
        "urine",
        "urinalysis",
        "urine routine",
        "urine microscopy",
        "calcium oxalate",
        "uric acid crystals",
        "kidney stone",
        "renal stone",
        "crystals"
    ]

    urine_detected = any(
        keyword in compact.lower()
        for keyword in urine_keywords
    )

    if urine_detected:

        findings.append(
            (
                "ℹ Kidney/urinary health markers are "
                "present in the report."
            )
        )

    # ========================================================
    # HAIR / DERMATOLOGY
    # ========================================================
    #
    # A laboratory report cannot by itself diagnose hair fall.
    # We only detect if relevant tests/terms are actually present.
    # ========================================================

    hair_keywords = [
        "ferritin",
        "iron profile",
        "vitamin b12",
        "vitamin d",
        "zinc",
        "thyroid",
        "hair loss",
        "alopecia"
    ]

    hair_related = any(
        keyword in compact.lower()
        for keyword in hair_keywords
    )

    if hair_related:

        findings.append(
            (
                "ℹ Hair-loss-related laboratory markers or "
                "terms were detected in the report."
            )
        )

    # ========================================================
    # GENERAL REPORT INFORMATION
    # ========================================================

    if not parameters:

        findings.append(
            (
                "ℹ No supported numerical health parameters "
                "were confidently detected."
            )
        )

    # ========================================================
    # SCORE
    # ========================================================

    score = max(
        0,
        min(
            100,
            int(score)
        )
    )

    # ========================================================
    # RISK
    # ========================================================

    if score >= 90:

        risk = "🟢 Low Risk"

    elif score >= 70:

        risk = "🟡 Medium Risk"

    else:

        risk = "🔴 High Risk"

    # ========================================================
    # DEFAULT RECOMMENDATION
    # ========================================================

    if not recommendations:

        recommendations.append(
            (
                "Continue routine health monitoring and "
                "follow your healthcare professional's advice."
            )
        )

    # ========================================================
    # RESULT
    # ========================================================

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

    # ========================================================
    # DEBUG OUTPUT
    # ========================================================

    print(
        "\n========== DETECTED PARAMETERS =========="
    )

    for name, value in parameters.items():

        print(
            f"{name}: {value}"
        )

    print(
        "\n========== FINDINGS =========="
    )

    for item in findings:

        print(item)

    print(
        "\nSCORE:",
        score
    )

    print(
        "RISK:",
        risk
    )

    print(
        "=========================================\n"
    )

    return result