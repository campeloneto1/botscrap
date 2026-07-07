"""
Script de migração para adicionar colunas faltantes.
Execute com: docker-compose exec backend python migrate.py
"""
import asyncio
from sqlalchemy import text
from app.db.database import engine


async def migrate():
    async with engine.begin() as conn:
        # Verificar e adicionar coluna username na tabela users
        result = await conn.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'users' AND column_name = 'username'
        """))
        if not result.fetchone():
            print("Adicionando coluna 'username' na tabela 'users'...")
            # Primeiro adiciona como nullable
            await conn.execute(text("""
                ALTER TABLE users ADD COLUMN username VARCHAR(100)
            """))
            # Preenche com base no email (parte antes do @)
            await conn.execute(text("""
                UPDATE users SET username = LOWER(SPLIT_PART(email, '@', 1))
                WHERE username IS NULL
            """))
            # Garante unicidade adicionando sufixo onde necessário
            await conn.execute(text("""
                UPDATE users u1 SET username = username || '_' || id
                WHERE EXISTS (
                    SELECT 1 FROM users u2
                    WHERE u2.username = u1.username AND u2.id < u1.id
                )
            """))
            # Agora torna NOT NULL e adiciona constraints
            await conn.execute(text("""
                ALTER TABLE users ALTER COLUMN username SET NOT NULL
            """))
            await conn.execute(text("""
                CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username ON users(username)
            """))
            print("Coluna 'username' adicionada com sucesso!")
        else:
            print("Coluna 'username' já existe.")

        # Verificar e adicionar coluna summary na tabela processed_posts
        result = await conn.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'processed_posts' AND column_name = 'summary'
        """))
        if not result.fetchone():
            print("Adicionando coluna 'summary' na tabela 'processed_posts'...")
            await conn.execute(text("""
                ALTER TABLE processed_posts ADD COLUMN summary TEXT
            """))
            print("Coluna 'summary' adicionada com sucesso!")
        else:
            print("Coluna 'summary' já existe.")

        # Tornar email nullable (se ainda não for)
        result = await conn.execute(text("""
            SELECT is_nullable FROM information_schema.columns
            WHERE table_name = 'users' AND column_name = 'email'
        """))
        row = result.fetchone()
        if row and row[0] == 'NO':
            print("Tornando coluna 'email' nullable...")
            await conn.execute(text("""
                ALTER TABLE users ALTER COLUMN email DROP NOT NULL
            """))
            print("Coluna 'email' agora é nullable!")
        else:
            print("Coluna 'email' já é nullable.")

    print("\nMigração concluída com sucesso!")


if __name__ == "__main__":
    asyncio.run(migrate())
