"""
Script de migração automática.
Verifica diferenças entre os models e o banco e aplica as alterações.
Roda automaticamente no startup do container.
"""
import asyncio
import logging
from sqlalchemy import text, inspect
from sqlalchemy.engine import Engine
from app.db.database import engine, Base
from app.db import models  # Importa todos os models

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Mapeamento de tipos SQLAlchemy para PostgreSQL
TYPE_MAP = {
    'INTEGER': 'INTEGER',
    'BIGINT': 'BIGINT',
    'SMALLINT': 'SMALLINT',
    'VARCHAR': 'VARCHAR',
    'STRING': 'VARCHAR',
    'TEXT': 'TEXT',
    'BOOLEAN': 'BOOLEAN',
    'DATETIME': 'TIMESTAMP',
    'DATE': 'DATE',
    'FLOAT': 'FLOAT',
    'NUMERIC': 'NUMERIC',
    'JSON': 'JSON',
}


def get_pg_type(column) -> str:
    """Converte tipo SQLAlchemy para tipo PostgreSQL."""
    type_name = type(column.type).__name__.upper()

    if type_name == 'VARCHAR' or type_name == 'STRING':
        length = getattr(column.type, 'length', None)
        if length:
            return f'VARCHAR({length})'
        return 'VARCHAR(255)'

    return TYPE_MAP.get(type_name, 'TEXT')


async def get_existing_columns(conn, table_name: str) -> dict:
    """Retorna as colunas existentes de uma tabela."""
    result = await conn.execute(text("""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_name = :table_name
    """), {"table_name": table_name})

    columns = {}
    for row in result.fetchall():
        columns[row[0]] = {
            'type': row[1],
            'nullable': row[2] == 'YES',
            'default': row[3],
        }
    return columns


async def table_exists(conn, table_name: str) -> bool:
    """Verifica se uma tabela existe."""
    result = await conn.execute(text("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = :table_name
        )
    """), {"table_name": table_name})
    return result.scalar()


async def migrate():
    """Executa as migrações automáticas."""
    logger.info("Iniciando verificação de migrações...")

    async with engine.begin() as conn:
        # Primeiro, cria todas as tabelas que não existem
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Tabelas base verificadas/criadas.")

        # Agora verifica colunas faltantes em cada tabela
        for table_name, table in Base.metadata.tables.items():
            if not await table_exists(conn, table_name):
                logger.info(f"Tabela '{table_name}' será criada pelo create_all")
                continue

            existing_columns = await get_existing_columns(conn, table_name)

            for column in table.columns:
                col_name = column.name

                if col_name not in existing_columns:
                    # Coluna não existe, precisa adicionar
                    pg_type = get_pg_type(column)
                    nullable = column.nullable if column.nullable is not None else True

                    logger.info(f"Adicionando coluna '{col_name}' ({pg_type}) na tabela '{table_name}'...")

                    # Monta o comando ALTER TABLE
                    null_constraint = "" if nullable else " NOT NULL"

                    # Se não é nullable, precisa de um valor default temporário
                    if not nullable and column.default is None:
                        if 'INT' in pg_type:
                            default_val = "DEFAULT 0"
                        elif 'BOOL' in pg_type:
                            default_val = "DEFAULT false"
                        elif 'VARCHAR' in pg_type or 'TEXT' in pg_type:
                            default_val = "DEFAULT ''"
                        else:
                            default_val = ""

                        await conn.execute(text(f"""
                            ALTER TABLE {table_name}
                            ADD COLUMN {col_name} {pg_type} {default_val}
                        """))

                        # Remove o default depois de adicionar
                        await conn.execute(text(f"""
                            ALTER TABLE {table_name}
                            ALTER COLUMN {col_name} DROP DEFAULT
                        """))

                        # Adiciona NOT NULL
                        await conn.execute(text(f"""
                            ALTER TABLE {table_name}
                            ALTER COLUMN {col_name} SET NOT NULL
                        """))
                    else:
                        default_clause = ""
                        if column.default is not None:
                            if hasattr(column.default, 'arg'):
                                default_val = column.default.arg
                                if isinstance(default_val, bool):
                                    default_clause = f" DEFAULT {str(default_val).lower()}"
                                elif isinstance(default_val, (int, float)):
                                    default_clause = f" DEFAULT {default_val}"
                                elif isinstance(default_val, str):
                                    default_clause = f" DEFAULT '{default_val}'"

                        await conn.execute(text(f"""
                            ALTER TABLE {table_name}
                            ADD COLUMN {col_name} {pg_type}{null_constraint}{default_clause}
                        """))

                    logger.info(f"Coluna '{col_name}' adicionada com sucesso!")
                else:
                    # Coluna existe, verificar se precisa de ajustes
                    existing = existing_columns[col_name]
                    model_nullable = column.nullable if column.nullable is not None else True

                    # Verificar nullable
                    if existing['nullable'] != model_nullable:
                        if model_nullable:
                            logger.info(f"Tornando coluna '{table_name}.{col_name}' nullable...")
                            await conn.execute(text(f"""
                                ALTER TABLE {table_name}
                                ALTER COLUMN {col_name} DROP NOT NULL
                            """))
                        # Não vamos forçar NOT NULL em colunas existentes para evitar erros

        # Verificar e criar índices faltantes
        for table_name, table in Base.metadata.tables.items():
            if not await table_exists(conn, table_name):
                continue

            for index in table.indexes:
                # Verificar se o índice já existe
                index_check = await conn.execute(text("""
                    SELECT 1 FROM pg_indexes
                    WHERE tablename = :table_name AND indexname = :index_name
                """), {"table_name": table_name, "index_name": index.name})

                if not index_check.scalar():
                    try:
                        # Criar o índice
                        columns = ", ".join([c.name for c in index.columns])
                        unique = "UNIQUE" if index.unique else ""
                        logger.info(f"Criando índice '{index.name}' na tabela '{table_name}'...")
                        await conn.execute(text(f"""
                            CREATE {unique} INDEX IF NOT EXISTS {index.name}
                            ON {table_name} ({columns})
                        """))
                        logger.info(f"Índice '{index.name}' criado com sucesso!")
                    except Exception as e:
                        logger.warning(f"Erro ao criar índice '{index.name}': {e}")

        logger.info("Migrações concluídas com sucesso!")


async def main():
    try:
        await migrate()
    except Exception as e:
        logger.error(f"Erro durante migração: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
