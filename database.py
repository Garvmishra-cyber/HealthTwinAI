import sqlite3


DATABASE = "healthtwin.db"


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection():

    conn = sqlite3.connect(DATABASE)

    conn.row_factory = sqlite3.Row

    return conn


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def init_database():

    conn = get_connection()

    cursor = conn.cursor()


    # ========================================================
    # USERS TABLE
    # ========================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT NOT NULL,

            email TEXT UNIQUE NOT NULL,

            password TEXT NOT NULL
        )
    """)


    # ========================================================
    # REPORTS TABLE
    # ========================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reports (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER,

            filename TEXT,

            hemoglobin TEXT,

            rbc TEXT,

            wbc TEXT,

            platelets TEXT,

            findings TEXT,

            recommendations TEXT,

            score INTEGER,

            risk TEXT,

            created_at TIMESTAMP
                DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (user_id)
                REFERENCES users(id)
        )
    """)


    # ========================================================
    # CHECK EXISTING REPORT COLUMNS
    # ========================================================

    cursor.execute(
        "PRAGMA table_info(reports)"
    )

    existing_columns = {

        row["name"]

        for row in cursor.fetchall()
    }


    # ========================================================
    # ADD MISSING COLUMNS
    # ========================================================

    required_columns = {

        "user_id":
            "INTEGER",

        "hemoglobin":
            "TEXT",

        "rbc":
            "TEXT",

        "wbc":
            "TEXT",

        "platelets":
            "TEXT"
    }


    for column, data_type in required_columns.items():

        if column not in existing_columns:

            cursor.execute(
                f"""
                ALTER TABLE reports
                ADD COLUMN {column} {data_type}
                """
            )


    # ========================================================
    # COMMIT
    # ========================================================

    conn.commit()

    conn.close()


# ============================================================
# SAVE REPORT
# ============================================================

def save_report(
    user_id,
    filename,
    parameters,
    score,
    risk,
    findings,
    recommendations
):

    conn = get_connection()

    cursor = conn.cursor()


    cursor.execute("""
        INSERT INTO reports
        (
            user_id,
            filename,
            hemoglobin,
            rbc,
            wbc,
            platelets,
            findings,
            recommendations,
            score,
            risk
        )

        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (

        user_id,

        filename,

        parameters.get(
            "Hemoglobin",
            "Not detected"
        ),

        parameters.get(
            "RBC",
            "Not detected"
        ),

        parameters.get(
            "WBC",
            "Not detected"
        ),

        parameters.get(
            "Platelets",
            "Not detected"
        ),

        "\n".join(findings),

        "\n".join(recommendations),

        score,

        risk
    ))


    conn.commit()

    report_id = cursor.lastrowid

    conn.close()


    return report_id


# ============================================================
# GET USER REPORTS
# ============================================================

def get_user_reports(user_id):

    conn = get_connection()

    cursor = conn.cursor()


    cursor.execute("""
        SELECT *

        FROM reports

        WHERE user_id = ?

        ORDER BY created_at DESC
    """, (
        user_id,
    ))


    reports = cursor.fetchall()

    conn.close()


    return reports