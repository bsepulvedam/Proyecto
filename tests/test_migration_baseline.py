import re
import unittest
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

from app.database.base import Base
import app.models  # noqa: F401


class MigrationBaselineTests(unittest.TestCase):
    def test_migration_history_is_single_linear_chain(self):
        scripts = ScriptDirectory.from_config(Config("alembic.ini"))
        self.assertEqual(scripts.get_heads(), ["20260830_06"])
        revisions = list(scripts.walk_revisions())
        self.assertEqual(len(revisions), 6)
        for newer, older in zip(revisions, revisions[1:]):
            self.assertEqual(newer.down_revision, older.revision)
        self.assertIsNone(revisions[-1].down_revision)

    def test_orm_tables_have_a_creating_migration(self):
        created_tables: set[str] = set()
        pattern = re.compile(r'op\.create_table\(\s*["\']([^"\']+)["\']')
        for migration in Path("alembic/versions").glob("*.py"):
            created_tables.update(
                pattern.findall(migration.read_text(encoding="utf-8"))
            )
        self.assertEqual(set(Base.metadata.tables), created_tables)


if __name__ == "__main__":
    unittest.main()
