from sqlalchemy import create_engine, text

# Cria a engine de conexão
engine = create_engine('postgresql://superset:superset@localhost:5432/superset')

# Testa a conexão com uma query simples
with engine.connect() as connection:
    result = connection.execute(text("SELECT 1"))
    print("Conexão bem-sucedida:", result.scalar())

