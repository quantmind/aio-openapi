"""Alembic migrations handler
"""
import os

from alembic.config import Config
from alembic import command as alembic_cmd


def get_template_directory():
    return os.path.dirname(os.path.realpath(__file__))


class Migration:

    def __init__(self, app):
        self.app = app
        self.cfg = create_config(app)

    def init(self):
        dirname = self.cfg.get_main_option('script_location')
        alembic_cmd.init(self.cfg, dirname, template='openapi')

    def show(self, revision):
        alembic_cmd.show(self.cfg, revision)

    def stamp(self, revision):
        alembic_cmd.stamp(self.cfg, revision)

    def revision(self, message, autogenerate=False, branch_label=None):
        alembic_cmd.revision(self.cfg, autogenerate=autogenerate,
                             message=message, branch_label=branch_label)

    def upgrade(self, revision):
        alembic_cmd.upgrade(self.cfg, revision)

    def downgrade(self, revision):
        alembic_cmd.downgrade(self.cfg, revision)

    def merge(self, message, branch_label=None, rev_id=None, revisions=None):
        alembic_cmd.merge(self.cfg, message=message,
                          branch_label=branch_label,
                          rev_id=rev_id, revisions=revisions)


def create_config(app):
    """Programmatically create Alembic config
    """
    cfg = Config()
    cfg.get_template_directory = get_template_directory
    migrations = os.path.join(app['cwd'], 'migrations')

    cfg.set_main_option('script_location', migrations)
    cfg.config_file_name = os.path.join(migrations, 'alembic.ini')
    engine = app['store']
    cfg.set_section_option('default', 'sqlalchemy.url', str(engine.url))
    # put database in main options
    cfg.set_main_option("databases", 'default')
    # create empty logging section to avoid raising errors in env.py
    cfg.set_section_option('logging', 'path', '')
    cfg.metadata = dict(default=app['metadata'])
    return cfg
