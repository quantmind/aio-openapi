"""Alembic migrations handler
"""
import os
from io import StringIO

from alembic import command as alembic_cmd
from alembic.config import Config


def get_template_directory():
    return os.path.dirname(os.path.realpath(__file__))


class Migration:
    def __init__(self, app):
        self.app = app
        self.cfg = create_config(app)

    def init(self):
        dirname = self.cfg.get_main_option("script_location")
        alembic_cmd.init(self.cfg, dirname, template="openapi")
        return self.message()

    def show(self, revision):
        alembic_cmd.show(self.cfg, revision)
        return self.message()

    def history(self):
        alembic_cmd.history(self.cfg)
        return self.message()

    def revision(self, message, autogenerate=False, branch_label=None):
        alembic_cmd.revision(
            self.cfg,
            autogenerate=autogenerate,
            message=message,
            branch_label=branch_label,
        )
        return self.message()

    def upgrade(self, revision):
        alembic_cmd.upgrade(self.cfg, revision)
        return self.message()

    def downgrade(self, revision):
        alembic_cmd.downgrade(self.cfg, revision)
        return self.message()

    def current(self, verbose=False):
        alembic_cmd.current(self.cfg, verbose=verbose)
        return self.message()

    def message(self):
        msg = self.cfg.stdout.getvalue()
        self.cfg.stdout.seek(0)
        self.cfg.stdout.truncate()
        return msg


def create_config(app):
    """Programmatically create Alembic config
    """
    cfg = Config(stdout=StringIO())
    cfg.get_template_directory = get_template_directory
    migrations = os.path.join(app["cwd"], "migrations")

    cfg.set_main_option("script_location", migrations)
    cfg.config_file_name = os.path.join(migrations, "alembic.ini")
    db = app["db"]
    cfg.set_section_option("default", "sqlalchemy.url", str(db.engine.url))
    # put database in main options
    cfg.set_main_option("databases", "default")
    # create empty logging section to avoid raising errors in env.py
    cfg.set_section_option("logging", "path", "")
    cfg.metadata = dict(default=db.metadata)
    return cfg
