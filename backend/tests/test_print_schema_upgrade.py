"""Upgrade legacy and current print schemas without replacing existing files."""

import importlib.util
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


@pytest.mark.parametrize("existing", [(), ("cover_key",), ("cover_key", "interior_key")])
def test_print_file_upgrade_preserves_legacy_data(existing):
    path = Path(__file__).parents[1] / "alembic/versions/0025_print_file_columns.py"
    spec = importlib.util.spec_from_file_location("print_file_upgrade", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = sa.create_engine("sqlite:///:memory:")
    metadata = sa.MetaData()
    table = sa.Table(
        "print_orders",
        metadata,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("file_key", sa.Text()),
        *(sa.Column(name, sa.Text()) for name in existing),
    )
    metadata.create_all(engine)
    with engine.begin() as connection:
        values = {"id": 1, "file_key": "legacy.pdf"}
        values.update({name: f"{name}.pdf" for name in existing})
        connection.execute(table.insert().values(**values))
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
            migration.upgrade()
        columns = {item["name"] for item in sa.inspect(connection).get_columns("print_orders")}
        assert {"file_key", "cover_key", "interior_key"} <= columns
        row = connection.execute(sa.text("select * from print_orders")).mappings().one()
        assert row["file_key"] == "legacy.pdf"
        for name in existing:
            assert row[name] == f"{name}.pdf"
