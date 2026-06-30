"""Database schema creation and version bootstrap."""

import sqlite3

from core.branding import DEFAULT_PROFILE_SEED
from core.db.connection import SCHEMA_VERSION, get_connection
from core.db.migrations import get_schema_version, migrate, set_schema_version


def init_database() -> None:
    """Initialize all tables if they don't exist. Seed default data."""
    conn = get_connection()
    cursor = conn.cursor()

    # Profiles
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            color TEXT DEFAULT '#14B8A6',
            profile_type TEXT DEFAULT 'personal' CHECK(profile_type IN ('personal', 'mei')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1
        )
    """)

    # Categories
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
            icon TEXT,
            is_mei_deductible INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(name, type)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mei_config (
            profile_id INTEGER PRIMARY KEY,
            razao_social TEXT NOT NULL,
            cnpj TEXT NOT NULL,
            activity_type TEXT NOT NULL CHECK(activity_type IN ('comercio', 'servico', 'industria', 'comercio_servico')),
            custom_das_amount REAL,
            annual_limit REAL DEFAULT 81000,
            das_day INTEGER DEFAULT 20,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mei_clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            document TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mei_invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id INTEGER NOT NULL,
            invoice_number TEXT NOT NULL,
            client_id INTEGER,
            tomador_name TEXT,
            amount REAL NOT NULL,
            issue_date DATE NOT NULL,
            due_date DATE,
            paid_at DATE,
            transaction_id INTEGER,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE,
            FOREIGN KEY (client_id) REFERENCES mei_clients(id) ON DELETE SET NULL,
            FOREIGN KEY (transaction_id) REFERENCES transactions(id) ON DELETE SET NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS assets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            asset_type TEXT NOT NULL DEFAULT 'other',
            current_value REAL NOT NULL DEFAULT 0,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS liabilities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            liability_type TEXT NOT NULL DEFAULT 'other',
            current_balance REAL NOT NULL DEFAULT 0,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS net_worth_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id INTEGER NOT NULL,
            snapshot_date DATE NOT NULL,
            total_assets REAL NOT NULL DEFAULT 0,
            total_liabilities REAL NOT NULL DEFAULT 0,
            net_worth REAL NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(profile_id, snapshot_date),
            FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
        )
    """)

    # Transactions
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id INTEGER NOT NULL,
            date DATE NOT NULL,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            category_id INTEGER NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
            is_recurring BOOLEAN DEFAULT 0,
            notes TEXT,
            is_installment INTEGER DEFAULT 0,
            installment_group_id TEXT,
            installment_number INTEGER,
            installment_total INTEGER,
            mei_client_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE,
            FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE RESTRICT,
            FOREIGN KEY (mei_client_id) REFERENCES mei_clients(id) ON DELETE SET NULL
        )
    """)

    # Simple key-value settings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    # Budgets per category/month
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id INTEGER,
            category_id INTEGER NOT NULL,
            year INTEGER NOT NULL,
            month INTEGER NOT NULL,
            monthly_limit REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(profile_id, category_id, year, month),
            FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE,
            FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
        )
    """)

    # Financial Goals
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id INTEGER,
            name TEXT NOT NULL,
            target_amount REAL NOT NULL,
            current_amount REAL DEFAULT 0,
            deadline DATE,
            is_completed BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
        )
    """)

    # Import history
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS import_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            transactions_imported INTEGER DEFAULT 0,
            profile_id INTEGER,
            FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE SET NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categorization_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            priority INTEGER DEFAULT 100,
            match_type TEXT NOT NULL CHECK(match_type IN ('contains', 'starts_with', 'equals')),
            pattern TEXT NOT NULL,
            category_id INTEGER NOT NULL,
            profile_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES categories(id),
            FOREIGN KEY (profile_id) REFERENCES profiles(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER NOT NULL
        )
    """)
    cursor.execute("SELECT COUNT(*) FROM schema_version")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO schema_version (version) VALUES (?)", (0,))

    current = get_schema_version(conn)
    if current < SCHEMA_VERSION:
        migrate(conn, current, SCHEMA_VERSION)
    else:
        set_schema_version(conn, current)

    conn.commit()

    # Seed default data if empty
    _seed_default_data(conn)
    conn.close()


def _seed_default_data(conn: sqlite3.Connection) -> None:
    """Seed initial profiles and categories if database is fresh."""
    cursor = conn.cursor()

    # Check if profiles exist
    cursor.execute("SELECT COUNT(*) FROM profiles")
    if cursor.fetchone()[0] == 0:
        for name, color in DEFAULT_PROFILE_SEED:
            cursor.execute(
                "INSERT INTO profiles (name, color) VALUES (?, ?)",
                (name, color),
            )

    # Check if categories exist
    cursor.execute("SELECT COUNT(*) FROM categories")
    if cursor.fetchone()[0] == 0:
        default_categories = [
            # Income
            ("Salário", "income", "💼"),
            ("Renda Extra / Freelance", "income", "💰"),
            ("Investimentos (Dividendos/Juros)", "income", "📈"),
            ("Aluguel Recebido", "income", "🏠"),
            ("Outros Rendimentos", "income", "📥"),
            # Expenses
            ("Moradia (Aluguel/Financiamento/Condomínio)", "expense", "🏡"),
            ("Alimentação (Mercado + Refeições)", "expense", "🛒"),
            ("Transporte (Combustível/Uber/Transporte Público)", "expense", "🚗"),
            ("Saúde (Plano + Medicamentos + Consultas)", "expense", "🏥"),
            ("Educação (Escola/Cursos)", "expense", "📚"),
            ("Lazer e Entretenimento", "expense", "🎮"),
            ("Assinaturas (Streaming, Apps, etc.)", "expense", "📱"),
            ("Utilities (Luz, Água, Gás, Internet)", "expense", "💡"),
            ("Seguros (Vida, Auto, Residencial)", "expense", "🛡️"),
            ("Roupas e Cuidados Pessoais", "expense", "👕"),
            ("Viagens e Férias", "expense", "✈️"),
            ("Presentes e Doações", "expense", "🎁"),
            ("Manutenção e Reparos", "expense", "🔧"),
            ("Impostos e Taxas", "expense", "📋"),
            ("Outros Gastos", "expense", "📦"),
        ]
        cursor.executemany(
            "INSERT INTO categories (name, type, icon) VALUES (?, ?, ?)",
            default_categories
        )

    conn.commit()