DB_USER = "postgres"
DB_PASSWORD = "password"
DB_HOST = "1.201.172.251"
DB_PORT = "5432"
DB_NAME = "dummy"


SQLALCHEMY_DATABASE_URI = 'postgresql+psycopg2://{user}:{pw}@{url}:{port}/{db}'.format(
    user=DB_USER,
    pw=DB_PASSWORD,
    url=DB_HOST,
    port=DB_PORT,
    db=DB_NAME)
