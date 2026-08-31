import hashlib
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
        self.assertEqual(scripts.get_heads(), ["20260831_07"])
        revisions = list(scripts.walk_revisions())
        self.assertEqual(len(revisions), 7)
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

    def test_historical_migrations_are_intact(self):
        expected = {
            "20260826_01_fase_4b_persistencia.py": "8d9b431755c01ce301a9d434f2504443476794888a3708b7dc1004a877768e90",
            "20260826_02_fase_4_inventario_base.py": "c0f564968ee757a7ffd16607903aee4715e6c5099d7d9d0f329b28253c1b9d69",
            "20260827_03_fase_7_movimientos_inventario.py": "30db8fb74c9347a58fbaf80312cc32350bec19939e12c011a926604f740d6342",
            "20260828_04_identidad_autenticacion_roles.py": "96118435870636fba2a55bc8570ffe5f3ac5367e11be8daaf6204b27c197e090",
            "20260829_05_password_temporal.py": "1ba6915d0e202d04bd1abc8ba1c5e61006ce33421b0b3fe4ba5d03fdd52d31a6",
            "20260830_06_asistencia_estructura.py": "76fe2fe8ee328b633e2668caac8d717f2f41c64a2bb4c468b85fee3ddda269da",
        }
        for filename, digest in expected.items():
            content = (Path("alembic/versions") / filename).read_bytes().replace(b"\r\n", b"\n")
            self.assertEqual(hashlib.sha256(content).hexdigest(), digest, filename)


if __name__ == "__main__":
    unittest.main()
