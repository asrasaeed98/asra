import os

os.environ.setdefault("DATABASE_URL", "sqlite://")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from findings_api.db import Base, get_db
from findings_api.main import app
from findings_api.models import CatalogResource


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    db = TestingSession()
    db.add(
        CatalogResource(
            id="test:1",
            portal="data_gov",
            title="Unemployment by State",
            description="State unemployment rates",
            organization="BLS via data.gov",
            tags=["economy"],
            format="CSV",
            license_normalized="CC0",
            license_raw="cc-zero",
            license_display="CC0 1.0",
            attribution_required=False,
            attribution_text="Source: BLS. https://catalog.data.gov/",
            publisher="BLS",
            source_url="https://catalog.data.gov/dataset/example",
            resource_url="https://example.com/data.csv",
            search_text="unemployment by state economy bls",
        )
    )
    db.commit()
    db.close()

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
