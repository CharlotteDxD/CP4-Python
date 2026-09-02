import os


class BaseConfig:
    """Configuração comum a todos os ambientes."""

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-troque-em-producao")

    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Anthony lê essa chave para chamar a API do LLM. Nunca commitar o valor
    # real — ele mora só no .env local / nas variáveis de ambiente do Render.
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class TestingConfig(BaseConfig):
    TESTING = True
    DEBUG = True
    # Testes não devem depender do Postgres do Render estar no ar.
    # SQLite em memória é suficiente para os testes de unidade/integração.
    SQLALCHEMY_DATABASE_URI = os.getenv("TEST_DATABASE_URL", "sqlite:///:memory:")


class ProductionConfig(BaseConfig):
    DEBUG = False


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
