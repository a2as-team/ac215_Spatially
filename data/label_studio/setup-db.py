#!/usr/bin/env python3
"""
Setup Label Studio database on PostgreSQL server.
Creates the database if it doesn't exist.

Usage:
    cd data
    python label_studio/setup-db.py
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from pathlib import Path


def load_env_file(env_path):
    """Load environment variables from .env file."""
    env_vars = {}
    with open(env_path, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                env_vars[key] = value
    return env_vars


def main():
    # Load database credentials from secrets (relative to data directory)
    secrets_dir = Path(__file__).parent.parent.parent / "secrets"
    env_file = secrets_dir / "spatially-postgres-db.env"
    labelstudio_env_file = secrets_dir / "spatially-labelstudio-db.env"

    env_vars = load_env_file(env_file)
    labelstudio_env_vars = load_env_file(labelstudio_env_file)

    host = env_vars.get("POSTGRE_HOST")
    port = env_vars.get("POSTGRE_PORT", "5432")
    user = env_vars.get("POSTGRE_USER")
    password = env_vars.get("POSTGRE_PASSWORD")
    db_name = labelstudio_env_vars.get("POSTGRE_NAME", "labelstudio")

    print(f"Connecting to PostgreSQL at {host}:{port} as {user}...")

    try:
        # Connect to default 'postgres' database
        conn = psycopg2.connect(
            host=host, port=port, user=user, password=password, database="postgres"
        )

        # Set isolation level to create database
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        # Check if database exists
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
        exists = cursor.fetchone()

        if exists:
            print(f"✓ Database '{db_name}' already exists")
        else:
            print(f"Creating database '{db_name}'...")
            cursor.execute(f"CREATE DATABASE {db_name}")
            print(f"✓ Database '{db_name}' created successfully")

        cursor.close()
        conn.close()

        print("\n✅ Label Studio database is ready!")
        print(f"   Database: {db_name}")
        print(f"   Host: {host}:{port}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
