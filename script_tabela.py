from sqlalchemy import create_engine, text

engine = create_engine('postgresql://superset:superset@localhost:5432/superset')

with engine.connect() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS exemplo_superset (
            id SERIAL PRIMARY KEY,
            nome TEXT,
            idade INTEGER
        )
    """))
    conn.execute(text("""
        INSERT INTO exemplo_superset (nome, idade)
        VALUES ('Araken', 42), ('Renan', 35)
    """))
    print("Tabela criada e dados inseridos.")

