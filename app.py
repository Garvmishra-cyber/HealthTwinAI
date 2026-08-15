from flask import (
    Flask,
    render_template,
    request,
    redirect,
    session,
    jsonify
)

import sqlite3

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    psycopg2 = None
    RealDictCursor = None
import os
import json
import uuid

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from modules.ocr import extract_text
from modules.analyzer import analyze_report
from modules.ai_assistant import ask_health_ai
from modules.health_insights import generate_health_insights


# =========================================================
# APP CONFIGURATION
# =========================================================

app = Flask(__name__)

app.secret_key = os.getenv(
    "FLASK_SECRET_KEY",
    "healthtwin-development-secret-key"
)

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
DATABASE = os.getenv("DATABASE_PATH", "healthtwin.db")
USE_POSTGRES = bool(DATABASE_URL)

if USE_POSTGRES and psycopg2 is None:
    raise RuntimeError(
        "DATABASE_URL is set, but psycopg2 is not installed. "
        "Add psycopg2-binary to requirements.txt."
    )

UPLOAD_FOLDER = os.getenv(
    "UPLOAD_FOLDER",
    "uploads"
)

MAX_FILE_SIZE = 10 * 1024 * 1024

app.config["MAX_CONTENT_LENGTH"] = MAX_FILE_SIZE


# =========================================================
# CREATE UPLOAD DIRECTORY
# =========================================================

os.makedirs(
    UPLOAD_FOLDER,
    exist_ok=True
)


# =========================================================
# DATABASE
# =========================================================

class PostgresConnection:
    """Small compatibility wrapper so existing ? placeholders keep working."""

    def __init__(self, url):
        self.conn = psycopg2.connect(url, cursor_factory=RealDictCursor)

    def execute(self, sql, params=()):
        sql = sql.replace("?", "%s")
        cursor = self.conn.cursor()
        cursor.execute(sql, params)
        return cursor

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def close(self):
        self.conn.close()


def get_db():
    if USE_POSTGRES:
        return PostgresConnection(DATABASE_URL)

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def is_duplicate_error(error):
    if USE_POSTGRES and psycopg2 is not None:
        return isinstance(error, psycopg2.errors.UniqueViolation)
    return isinstance(error, sqlite3.IntegrityError)


# =========================================================
# DATABASE SETUP
# =========================================================

def ensure_database():
    conn = get_db()

    if USE_POSTGRES:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reports (
                id SERIAL PRIMARY KEY,
                filename TEXT,
                findings TEXT,
                recommendations TEXT,
                score INTEGER,
                risk TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_id INTEGER,
                report_text TEXT,
                parameters TEXT
            )
            """
        )
    else:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT,
                findings TEXT,
                recommendations TEXT,
                score INTEGER,
                risk TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_id INTEGER,
                report_text TEXT,
                parameters TEXT
            )
            """
        )

        columns = [
            row["name"]
            for row in conn.execute("PRAGMA table_info(reports)").fetchall()
        ]
        for column, data_type in {
            "user_id": "INTEGER",
            "report_text": "TEXT",
            "parameters": "TEXT"
        }.items():
            if column not in columns:
                try:
                    conn.execute(
                        f"ALTER TABLE reports ADD COLUMN {column} {data_type}"
                    )
                except sqlite3.OperationalError:
                    pass

    conn.commit()
    conn.close()


# =========================================================
# INITIALIZE DATABASE ON APP START
# =========================================================
# Required for Gunicorn/Render imports.
ensure_database()


# =========================================================
# NORMALIZE PARAMETERS
# =========================================================

def normalize_parameters(parameters):

    if not isinstance(
        parameters,
        dict
    ):

        parameters = {}

    normalized = {}

    for key, value in parameters.items():

        clean_key = str(
            key
        ).lower().strip()

        clean_key = clean_key.replace(
            "_",
            " "
        )

        clean_key = clean_key.replace(
            "-",
            " "
        )

        # -------------------------------------------------
        # HEMOGLOBIN
        # -------------------------------------------------

        if (

            "hemoglobin" in clean_key

            or "haemoglobin" in clean_key

            or clean_key == "hb"

        ):

            normalized["Hemoglobin"] = value

        # -------------------------------------------------
        # RBC
        # -------------------------------------------------

        elif (

            clean_key == "rbc"

            or "total rbc" in clean_key

            or "red blood cell" in clean_key

        ):

            normalized["RBC"] = value

        # -------------------------------------------------
        # WBC
        # -------------------------------------------------

        elif (

            clean_key == "wbc"

            or "total wbc" in clean_key

            or "white blood cell" in clean_key

        ):

            normalized["WBC"] = value

        # -------------------------------------------------
        # PLATELETS
        # -------------------------------------------------

        elif (

            "platelet" in clean_key

            or clean_key == "plt"

        ):

            normalized["Platelets"] = value

    normalized.setdefault(
        "Hemoglobin",
        "0"
    )

    normalized.setdefault(
        "RBC",
        "0"
    )

    normalized.setdefault(
        "WBC",
        "0"
    )

    normalized.setdefault(
        "Platelets",
        "0"
    )

    return normalized


# =========================================================
# PREPARE REPORT
# =========================================================

def prepare_report(report):

    parameters = {}

    if report["parameters"]:

        try:

            parameters = json.loads(
                report["parameters"]
            )

        except Exception:

            parameters = {}

    parameters = normalize_parameters(
        parameters
    )

    return {

        "id":
            report["id"],

        "filename":
            report["filename"],

        "score":
            report["score"],

        "risk":
            report["risk"],

        "parameters":
            parameters,

        "created_at":
            report["created_at"]

    }


# =========================================================
# LOCAL CHAT FALLBACK
# =========================================================

def local_chat_reply(
    message,
    report
):

    message = message.lower().strip()

    parameters = {}

    if report["parameters"]:

        try:

            parameters = json.loads(
                report["parameters"]
            )

        except Exception:

            parameters = {}

    parameters = normalize_parameters(
        parameters
    )

    hemoglobin = parameters[
        "Hemoglobin"
    ]

    rbc = parameters[
        "RBC"
    ]

    wbc = parameters[
        "WBC"
    ]

    platelets = parameters[
        "Platelets"
    ]

    score = report["score"]

    risk = report["risk"]

    # -----------------------------------------------------
    # HEALTH SCORE
    # -----------------------------------------------------

    if (

        "health score" in message

        or "score" in message

    ):

        return (

            f"Your latest Health Score is "
            f"{score}/100. "
            f"The recorded risk level is "
            f"{risk}."
        )

    # -----------------------------------------------------
    # HEMOGLOBIN
    # -----------------------------------------------------

    if (

        "hemoglobin" in message

        or "haemoglobin" in message

        or " hb " in
        f" {message} "

    ):

        return (

            f"Your latest recorded Hemoglobin "
            f"value is {hemoglobin} g/dL. "
            f"Please compare it with the reference "
            f"range printed on your report."
        )

    # -----------------------------------------------------
    # WBC
    # -----------------------------------------------------

    if (

        "wbc" in message

        or "white blood" in message

        or "white cell" in message

    ):

        return (

            f"Your latest recorded WBC count is "
            f"{wbc}/µL. "
            f"Please compare it with the reference "
            f"range on your report."
        )

    # -----------------------------------------------------
    # RBC
    # -----------------------------------------------------

    if (

        "rbc" in message

        or "red blood" in message

        or "red cell" in message

    ):

        return (

            f"Your latest recorded RBC count is "
            f"{rbc}. "
            f"Please compare it with the reference "
            f"range on your report."
        )

    # -----------------------------------------------------
    # PLATELETS
    # -----------------------------------------------------

    if (

        "platelet" in message

        or "plt" in message

    ):

        return (

            f"Your latest recorded Platelet count "
            f"is {platelets}/µL. "
            f"Please compare it with the reference "
            f"range on your report."
        )

    # -----------------------------------------------------
    # SUMMARY
    # -----------------------------------------------------

    if (

        "summary" in message

        or "summarize" in message

        or "overview" in message

        or "report" in message

    ):

        return (

            "Latest Report Summary\n\n"

            f"Health Score: "
            f"{score}/100\n"

            f"Risk Level: "
            f"{risk}\n"

            f"Hemoglobin: "
            f"{hemoglobin}\n"

            f"RBC: "
            f"{rbc}\n"

            f"WBC: "
            f"{wbc}\n"

            f"Platelets: "
            f"{platelets}"
        )

    # -----------------------------------------------------
    # DEFAULT
    # -----------------------------------------------------

    return (

        "I can help you understand your "
        "uploaded report.\n\n"

        "Try asking:\n"

        "• What is my health score?\n"

        "• What is my hemoglobin?\n"

        "• What is my WBC?\n"

        "• What is my RBC?\n"

        "• What are my platelets?\n"

        "• Give me a report summary."
    )


# =========================================================
# LOGIN
# =========================================================

@app.route(
    "/",
    methods=["GET", "POST"]
)
def login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        conn = get_db()

        user = conn.execute(
            """
            SELECT *
            FROM users
            WHERE email = ?
            """,
            (email,)
        ).fetchone()

        conn.close()

        if user:

            valid = False

            try:

                valid = check_password_hash(
                    user["password"],
                    password
                )

            except Exception:

                valid = False

            # ------------------------------------------------
            # OLD PLAIN TEXT PASSWORD COMPATIBILITY
            # ------------------------------------------------

            if not valid:

                if user["password"] == password:

                    valid = True

                    new_hash = (
                        generate_password_hash(
                            password
                        )
                    )

                    conn = get_db()

                    conn.execute(
                        """
                        UPDATE users
                        SET password = ?
                        WHERE id = ?
                        """,
                        (
                            new_hash,
                            user["id"]
                        )
                    )

                    conn.commit()

                    conn.close()

            if valid:

                session["user_id"] = user["id"]

                session["user_name"] = user["name"]

                return redirect(
                    "/dashboard"
                )

        return (
            "Invalid Email or Password",
            401
        )

    return render_template(
        "login.html"
    )


# =========================================================
# REGISTER
# =========================================================

@app.route(
    "/register",
    methods=["GET", "POST"]
)
def register():

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        if not name:

            return "Name is required."

        if not email:

            return "Email is required."

        if not password:

            return "Password is required."

        if len(password) < 6:

            return (
                "Password must contain "
                "at least 6 characters."
            )

        password_hash = (
            generate_password_hash(
                password
            )
        )

        conn = get_db()

        try:

            conn.execute(
                """
                INSERT INTO users
                (
                    name,
                    email,
                    password
                )
                VALUES (?, ?, ?)
                """,
                (
                    name,
                    email,
                    password_hash
                )
            )

            conn.commit()

        except Exception as error:
            if not is_duplicate_error(error):
                conn.rollback()
                conn.close()
                print("REGISTER DATABASE ERROR:", error)
                return "Registration failed. Please try again.", 500

            conn.close()

            return (
                "This email is already registered."
            )

        conn.close()

        return redirect("/")

    return render_template(
        "register.html"
    )


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:

        return redirect("/")

    conn = get_db()

    latest_report = conn.execute(
        """
        SELECT *
        FROM reports
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (
            session["user_id"],
        )
    ).fetchone()

    conn.close()

    parameters = {

        "Hemoglobin": "0",

        "RBC": "0",

        "WBC": "0",

        "Platelets": "0"

    }

    if latest_report:

        if latest_report["parameters"]:

            try:

                parameters = json.loads(
                    latest_report["parameters"]
                )

            except Exception:

                parameters = {}

        parameters = normalize_parameters(
            parameters
        )

    return render_template(

        "dashboard.html",

        name=session.get(
            "user_name",
            "User"
        ),

        latest_report=latest_report,

        parameters=parameters

    )


# =========================================================
# UPLOAD REPORT
# =========================================================

@app.route(
    "/upload",
    methods=["GET", "POST"]
)
def upload():

    if "user_id" not in session:

        return redirect("/")

    if request.method == "POST":

        file = request.files.get(
            "report"
        )

        if not file:

            return (
                "Please select a report."
            )

        if not file.filename:

            return (
                "Please select a report."
            )

        # -------------------------------------------------
        # SAFE UNIQUE FILENAME
        # -------------------------------------------------

        original_name = file.filename

        extension = os.path.splitext(
            original_name
        )[1].lower()

        allowed_extensions = {

            ".pdf",

            ".png",

            ".jpg",

            ".jpeg",

            ".webp"

        }

        if extension not in allowed_extensions:

            return (
                "Unsupported file type. "
                "Please upload PDF or image."
            )

        unique_name = (
            str(uuid.uuid4())
            + extension
        )

        filepath = os.path.join(
            UPLOAD_FOLDER,
            unique_name
        )

        file.save(filepath)

        # -------------------------------------------------
        # OCR
        # -------------------------------------------------

        try:

            extracted_text = extract_text(
                filepath
            )

        except Exception as error:

            print(
                "OCR ERROR:",
                error
            )

            return (
                "OCR failed. "
                "Please check the uploaded file."
            )

        # -------------------------------------------------
        # ANALYSIS
        # -------------------------------------------------

        try:

            report = analyze_report(
                extracted_text
            )

        except Exception as error:

            print(
                "ANALYZER ERROR:",
                error
            )

            return (
                "Report analysis failed."
            )

        parameters = normalize_parameters(
            report.get(
                "parameters",
                {}
            )
        )

        findings = report.get(
            "findings",
            []
        )

        recommendations = report.get(
            "recommendations",
            []
        )

        score = report.get(
            "score",
            0
        )

        risk = report.get(
            "risk",
            "Unknown"
        )

        # -------------------------------------------------
        # SAVE REPORT
        # -------------------------------------------------

        conn = get_db()

        conn.execute(
            """
            INSERT INTO reports
            (
                filename,
                findings,
                recommendations,
                score,
                risk,
                user_id,
                report_text,
                parameters
            )
             VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                original_name,

                "\n".join(
                    str(x)
                    for x in findings
                ),

                "\n".join(
                    str(x)
                    for x in recommendations
                ),

                score,

                risk,

                session["user_id"],

                extracted_text,

                json.dumps(
                    parameters
                )

            )
        )

        conn.commit()

        conn.close()

        return render_template(

            "result.html",

            report_text=extracted_text,

            parameters=parameters,

            findings=findings,

            recommendations=recommendations,

            score=score,

            risk=risk

        )

    return render_template(
        "upload.html"
    )


# =========================================================
# HISTORY
# =========================================================

@app.route("/history")
def history():

    if "user_id" not in session:

        return redirect("/")

    conn = get_db()

    reports = conn.execute(
        """
        SELECT *
        FROM reports
        WHERE user_id = ?
        ORDER BY id DESC
        """,
        (
            session["user_id"],
        )
    ).fetchall()

    conn.close()

    return render_template(

        "history.html",

        reports=reports

    )


# =========================================================
# REPORT DETAILS
# =========================================================

@app.route(
    "/report/<int:report_id>"
)
def report_details(report_id):

    if "user_id" not in session:

        return redirect("/")

    conn = get_db()

    report = conn.execute(
        """
        SELECT *
        FROM reports
        WHERE id = ?
        AND user_id = ?
        """,
        (
            report_id,
            session["user_id"]
        )
    ).fetchone()

    conn.close()

    if not report:

        return (
            "Report not found.",
            404
        )

    parameters = {}

    if report["parameters"]:

        try:

            parameters = json.loads(
                report["parameters"]
            )

        except Exception:

            parameters = {}

    parameters = normalize_parameters(
        parameters
    )

    findings = []

    if report["findings"]:

        findings = [

            item.strip()

            for item in
            report["findings"].split("\n")

            if item.strip()

        ]

    recommendations = []

    if report["recommendations"]:

        recommendations = [

            item.strip()

            for item in
            report["recommendations"].split("\n")

            if item.strip()

        ]

    return render_template(

        "report_details.html",

        report=report,

        parameters=parameters,

        findings=findings,

        recommendations=recommendations

    )


# =========================================================
# DIGITAL TWIN / HEALTH TREND
# =========================================================

@app.route("/health-trend")
def health_trend():

    if "user_id" not in session:

        return redirect("/")

    conn = get_db()

    reports = conn.execute(
        """
        SELECT *
        FROM reports
        WHERE user_id = ?
        ORDER BY id ASC
        """,
        (
            session["user_id"],
        )
    ).fetchall()

    conn.close()

    trend_data = []

    for report in reports:

        prepared = prepare_report(
            report
        )

        trend_data.append({

            "id":
                prepared["id"],

            "date":
                prepared["created_at"],

            "filename":
                prepared["filename"],

            "score":
                prepared["score"],

            "risk":
                prepared["risk"],

            "hemoglobin":
                prepared["parameters"][
                    "Hemoglobin"
                ],

            "rbc":
                prepared["parameters"][
                    "RBC"
                ],

            "wbc":
                prepared["parameters"][
                    "WBC"
                ],

            "platelets":
                prepared["parameters"][
                    "Platelets"
                ]

        })

    # -----------------------------------------------------
    # SMART INSIGHTS
    # -----------------------------------------------------

    insights = []

    previous_report = None

    current_report = None

    if len(reports) >= 1:

        current_report = prepare_report(
            reports[-1]
        )

    if len(reports) >= 2:

        previous_report = prepare_report(
            reports[-2]
        )

    if current_report:

        try:

            insights = (
                generate_health_insights(

                    previous_report,

                    current_report

                )
            )

        except Exception as error:

            print(
                "INSIGHTS ERROR:",
                error
            )

            insights = [

                {

                    "title":
                        "Smart Tracking",

                    "message":
                        "Health tracking is available "
                        "for your uploaded reports.",

                    "type":
                        "info"

                }

            ]

    return render_template(

        "health_trend.html",

        trend_data=trend_data,

        insights=insights

    )


# =========================================================
# CHATBOT PAGE
# =========================================================

@app.route("/chatbot")
def chatbot():

    if "user_id" not in session:

        return redirect("/")

    return render_template(

        "chatbot.html",

        name=session.get(
            "user_name",
            "User"
        )

    )


# =========================================================
# CHAT API
# =========================================================

@app.route(
    "/chat",
    methods=["POST"]
)
def chat():

    if "user_id" not in session:

        return jsonify({

            "reply":
                "Please login first."

        }), 401

    data = request.get_json(
        silent=True
    )

    if not data:

        return jsonify({

            "reply":
                "Please send a message."

        }), 400

    message = str(
        data.get(
            "message",
            ""
        )
    ).strip()

    if not message:

        return jsonify({

            "reply":
                "Please type a question."

        }), 400

    conn = get_db()

    report = conn.execute(
        """
        SELECT *
        FROM reports
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (
            session["user_id"],
        )
    ).fetchone()

    conn.close()

    if not report:

        return jsonify({

            "reply":
                "Please upload a report first."

        })

    # -----------------------------------------------------
    # LOCAL FALLBACK
    # -----------------------------------------------------

    local_reply = local_chat_reply(

        message,

        report

    )

    # -----------------------------------------------------
    # REPORT CONTEXT
    # -----------------------------------------------------

    parameters = {}

    if report["parameters"]:

        try:

            parameters = json.loads(
                report["parameters"]
            )

        except Exception:

            parameters = {}

    parameters = normalize_parameters(
        parameters
    )

    report_context = f"""

LATEST HEALTH REPORT

Health Score:
{report["score"]}/100

Risk Level:
{report["risk"]}

Hemoglobin:
{parameters["Hemoglobin"]}

RBC:
{parameters["RBC"]}

WBC:
{parameters["WBC"]}

Platelets:
{parameters["Platelets"]}

Findings:
{report["findings"]}

Recommendations:
{report["recommendations"]}

"""

    # -----------------------------------------------------
    # TRY AI
    # -----------------------------------------------------

    try:

        ai_reply = ask_health_ai(

            user_message=message,

            report_context=report_context

        )

        if (

            not ai_reply

            or "couldn't connect"
            in ai_reply.lower()

            or "could not connect"
            in ai_reply.lower()

            or "ai service"
            in ai_reply.lower()

            or "try again"
            in ai_reply.lower()

        ):

            return jsonify({

                "reply":
                    local_reply,

                "source":
                    "local"

            })

        return jsonify({

            "reply":
                ai_reply,

            "source":
                "ai"

        })

    except Exception as error:

        print(
            "AI unavailable:",
            error
        )

        return jsonify({

            "reply":
                local_reply,

            "source":
                "local"

        })


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


# =========================================================
# ERROR HANDLERS
# =========================================================

@app.errorhandler(404)
def page_not_found(error):

    return (

        "Page not found.",

        404

    )


@app.errorhandler(413)
def file_too_large(error):

    return (

        "File is too large. "
        "Maximum allowed size is 10 MB.",

        413

    )


@app.errorhandler(500)
def internal_error(error):

    return (

        "Internal server error. "
        "Please check the server logs.",

        500

    )


# =========================================================
# START SERVER
# =========================================================

if __name__ == "__main__":

    ensure_database()

    port = int(
        os.getenv(
            "PORT",
            "5000"
        )
    )

    app.run(

        host="0.0.0.0",

        port=port,

        debug=False

    )