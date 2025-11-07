from sqlalchemy import text
from database.connection import engine

def setup_pgvector():
    with engine.connect() as conn:
        print("Setting up pgvector...")

        try:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            conn.commit()
            print("✓ pgvector extension enabled")
        except Exception as e:
            print(f"✗ Error enabling pgvector: {e}")
            print("  Make sure pgvector is installed in PostgreSQL")
            return False

        try:
            result = conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='chunks' AND column_name='embedding_vector';
            """))

            if not result.fetchone():
                conn.execute(text("""
                    ALTER TABLE chunks
                    ADD COLUMN embedding_vector vector(1536);
                """))
                print("✓ Column embedding_vector added")
            else:
                print("ℹ Column embedding_vector already exists")

            conn.commit()
        except Exception as e:
            print(f"✗ Error adding column: {e}")
            return False

        try:
            conn.execute(text("DROP INDEX IF EXISTS chunks_embedding_vector_idx;"))
            conn.execute(text("""
                CREATE INDEX chunks_embedding_vector_idx
                ON chunks
                USING ivfflat (embedding_vector vector_cosine_ops)
                WITH (lists = 100);
            """))
            print("✓ IVFFlat index created")
            conn.commit()
        except Exception as e:
            print(f"⚠ Error creating index (normal if no data): {e}")

        try:
            result = conn.execute(text("SELECT COUNT(*) FROM chunks WHERE embedding_vector IS NOT NULL;"))
            count = result.scalar()
            print(f"\n📊 Status: {count} chunks with vector embeddings")
        except Exception as e:
            print(f"Could not check status: {e}")

        print("\n✓ Setup completed!")
        return True

if __name__ == "__main__":
    success = setup_pgvector()
    if not success:
        print("\n✗ Setup failed. Check if:")
        print("  1. PostgreSQL is running")
        print("  2. pgvector is installed: https://github.com/pgvector/pgvector")
        print("  3. Credentials are correct in .env")
