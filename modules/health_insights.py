def safe_float(value):

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def compare_value(
    name,
    previous,
    current
):

    previous_value = safe_float(previous)
    current_value = safe_float(current)

    if previous_value is None or current_value is None:

        return {
            "name": name,
            "previous": previous,
            "current": current,
            "change": None,
            "status": "Unavailable",
            "message": f"{name} comparison is unavailable."
        }

    change = current_value - previous_value

    if change > 0:

        status = "Increased"

        message = (
            f"{name} increased from "
            f"{previous} to {current}."
        )

    elif change < 0:

        status = "Decreased"

        message = (
            f"{name} decreased from "
            f"{previous} to {current}."
        )

    else:

        status = "Stable"

        message = (
            f"{name} remained stable at "
            f"{current}."
        )

    return {

        "name": name,

        "previous": previous,

        "current": current,

        "change": round(
            change,
            2
        ),

        "status": status,

        "message": message

    }


def generate_health_insights(
    previous_report,
    current_report
):

    insights = []

    if not previous_report or not current_report:

        return [

            {
                "title": "Not Enough Data",

                "message":
                "Upload at least two reports to "
                "compare health changes over time.",

                "type": "info"
            }

        ]

    # -----------------------------------------------------
    # HEALTH SCORE
    # -----------------------------------------------------

    previous_score = safe_float(
        previous_report.get("score")
    )

    current_score = safe_float(
        current_report.get("score")
    )

    if (
        previous_score is not None
        and current_score is not None
    ):

        score_change = (
            current_score
            - previous_score
        )

        if score_change > 0:

            insights.append({

                "title":
                "📈 Health Score Improved",

                "message":
                f"Your recorded Health Score "
                f"increased from "
                f"{previous_score}/100 to "
                f"{current_score}/100.",

                "type": "positive"

            })

        elif score_change < 0:

            insights.append({

                "title":
                "📉 Health Score Decreased",

                "message":
                f"Your recorded Health Score "
                f"changed from "
                f"{previous_score}/100 to "
                f"{current_score}/100.",

                "type": "warning"

            })

        else:

            insights.append({

                "title":
                "➡️ Health Score Stable",

                "message":
                f"Your recorded Health Score "
                f"remained at "
                f"{current_score}/100.",

                "type": "info"

            })

    # -----------------------------------------------------
    # PARAMETERS
    # -----------------------------------------------------

    previous_parameters = (
        previous_report.get(
            "parameters",
            {}
        )
    )

    current_parameters = (
        current_report.get(
            "parameters",
            {}
        )
    )

    parameter_names = [

        "Hemoglobin",

        "RBC",

        "WBC",

        "Platelets"

    ]

    for name in parameter_names:

        comparison = compare_value(

            name,

            previous_parameters.get(
                name,
                "N/A"
            ),

            current_parameters.get(
                name,
                "N/A"
            )

        )

        if comparison["change"] is None:

            continue

        if comparison["change"] == 0:

            insight_type = "info"

        else:

            insight_type = "neutral"

        insights.append({

            "title":
            f"🔎 {name}",

            "message":
            comparison["message"],

            "type":
            insight_type

        })

    # -----------------------------------------------------
    # GENERAL
    # -----------------------------------------------------

    insights.append({

        "title":
        "🧠 Smart Tracking",

        "message":
        "These comparisons are based on recorded "
        "report values and are intended for "
        "health tracking, not medical diagnosis.",

        "type":
        "info"

    })

    return insights