import sqlite3
import pandas as pd
from datetime import datetime
from pathlib import Path

class DBManager:
    """
    Handles all database operations for project tracking and analysis results.
    The database file is stored in the central data directory.
    """
    def __init__(self, db_path: Path):
        self.db_path = db_path
        # Ensure the directory for the database exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        """
        Initializes the database schema if it doesn't exist.
        """
        query_projects = """
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'PENDING'
        );
        """
        query_results = """
        CREATE TABLE IF NOT EXISTS analysis_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_name TEXT NOT NULL,
            module_type TEXT NOT NULL, -- 'VEG', 'GAS', 'THERMAL', 'GROUND'
            latitude REAL,
            longitude REAL,
            severity TEXT, -- 'LOW', 'MEDIUM', 'HIGH'
            description TEXT,
            detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_name) REFERENCES projects (name)
        );
        """
        with self._get_connection() as conn:
            conn.execute(query_projects)
            conn.execute(query_results)

    def register_project(self, name: str):
        """
        Registers a new project in the system.
        """
        query = "INSERT OR IGNORE INTO projects (name, status) VALUES (?, 'PENDING')"
        with self._get_connection() as conn:
            conn.execute(query, (name,))

    def update_project_status(self, name: str, status: str):
        """
        Updates the status of a project (e.g., 'PROCESSING', 'COMPLETED', 'FAILED').
        """
        query = "UPDATE projects SET status = ? WHERE name = ?"
        with self._get_connection() as conn:
            conn.execute(query, (status, name))

    def get_pending_projects(self):
        """
        Returns a list of projects that are waiting for processing.
        """
        query = "SELECT name FROM projects WHERE status = 'PENDING'"
        with self._get_connection() as conn:
            return [row[0] for row in conn.execute(query).fetchall()]

    def save_analysis_result(self, project_name: str, module: str, lat: float, lon: float, sev: str, desc: str):
        """
        Saves a single detection result to the database.
        """
        query = """
        INSERT INTO analysis_results (project_name, module_type, latitude, longitude, severity, description)
        VALUES (?, ?, ?, ?, ?, ?)
        """
        with self._get_connection() as conn:
            conn.execute(query, (project_name, module, lat, lon, sev, desc))

    def get_results_for_project(self, project_name: str, module: str = None):
        """
        Fetches results for a specific project, optionally filtered by module.
        Returns a Pandas DataFrame for easy use in Streamlit.
        """
        query = "SELECT * FROM analysis_results WHERE project_name = ?"
        params = [project_name]

        if module:
            query += " AND module_type = ?"
            params.append(module)

        with self._get_connection() as conn:
            return pd.read_sql_query(query, conn, params=params)