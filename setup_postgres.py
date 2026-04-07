"""
Database setup script for PostgreSQL
Creates database and user if they don't exist
"""
import os
import sys
import subprocess
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Database configuration
DB_NAME = os.getenv('DB_NAME', 'mybank')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'postgres')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')


def create_database():
    """Create PostgreSQL database and user"""
    
    print("🔧 Setting up PostgreSQL database...")
    print(f"   Database: {DB_NAME}")
    print(f"   User: {DB_USER}")
    print(f"   Host: {DB_HOST}:{DB_PORT}")
    
    try:
        # Connect to default postgres database
        conn = psycopg2.connect(
            dbname='postgres',
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Create database if not exists
        cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = '{DB_NAME}'")
        exists = cursor.fetchone()
        
        if not exists:
            print(f"📦 Creating database '{DB_NAME}'...")
            cursor.execute(f"CREATE DATABASE {DB_NAME}")
            print("✅ Database created")
        else:
            print(f"ℹ️  Database '{DB_NAME}' already exists")
        
        cursor.close()
        conn.close()
        
        # Set environment variable for the app
        database_url = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        print(f"\n🔗 Connection string:")
        print(f"   {database_url}")
        print(f"\n📝 Add to your environment:")
        print(f"   DATABASE_URL={database_url}")
        
        return True
        
    except psycopg2.OperationalError as e:
        print(f"❌ Failed to connect to PostgreSQL: {e}")
        print("\n💡 Make sure PostgreSQL is running:")
        print("   Windows: Check Services -> PostgreSQL")
        print("   Docker: docker run --name postgres -e POSTGRES_PASSWORD=postgres -p 5432:5432 -d postgres")
        return False


def test_connection():
    """Test database connection"""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not set")
        return False
    
    try:
        import psycopg2
        from urllib.parse import urlparse
        
        parsed = urlparse(database_url)
        conn = psycopg2.connect(
            dbname=parsed.path[1:],
            user=parsed.username,
            password=parsed.password,
            host=parsed.hostname,
            port=parsed.port
        )
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        print(f"✅ Connected to PostgreSQL {version[0]}")
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False


def init_db():
    """Initialize database tables"""
    print("\n🔄 Initializing database tables...")
    
    # Set environment variable
    database_url = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    os.environ['DATABASE_URL'] = database_url
    
    try:
        from database import Database
        db = Database()
        print("✅ Database tables created")
        return True
    except Exception as e:
        print(f"❌ Failed to initialize tables: {e}")
        return False


if __name__ == '__main__':
    print("=" * 50)
    print("MyBank - PostgreSQL Setup")
    print("=" * 50)
    print()
    
    # Create database
    if create_database():
        # Test connection
        if test_connection():
            # Initialize tables
            init_db()
            print("\n✅ PostgreSQL setup complete!")
        else:
            sys.exit(1)
    else:
        sys.exit(1)
