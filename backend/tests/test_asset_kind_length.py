"""assets.kind must store the rejected editorial candidate."""

import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

REJECTED_KIND = "editorial_rejected"


def test_asset_kind_widens_for_editorial_rejected():
    path = Path(__file__).parents[1] / "alembic/versions/0031_asset_kind_length.py"
    spec = importlib.util.spec_from_file_location("asset_kind_length", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    assert len(REJECTED_KIND) > 16
    engine = sa.create_engine("sqlite:///:memory:")
    metadata = sa.MetaData()
    table = sa.Table(
        "assets",
        metadata,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("kind", sa.String(16), nullable=False),
    )
    metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(table.insert().values(id=1, kind="cover"))
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
        kind = next(
            column
            for column in sa.inspect(connection).get_columns("assets")
            if column["name"] == "kind"
        )
        assert kind["type"].length == 32
        connection.execute(table.insert().values(id=2, kind=REJECTED_KIND))
        stored = connection.execute(sa.text("select kind from assets where id = 2")).scalar()
        assert stored == REJECTED_KIND
        kept = connection.execute(sa.text("select kind from assets where id = 1")).scalar()
        assert kept == "cover"
