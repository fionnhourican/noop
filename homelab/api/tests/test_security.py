"""Test security and authentication."""

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.security import get_current_ingestion_token, get_current_dashboard_user
from app.config import settings

test_app = FastAPI()


@test_app.get("/test/ingestion")
async def protected_ingestion(_: str = Depends(get_current_ingestion_token)):
    return {"message": "ingestion authorized"}


@test_app.get("/test/dashboard")
async def protected_dashboard(_: str = Depends(get_current_dashboard_user)):
    return {"message": "dashboard authorized"}


client = TestClient(test_app)


def test_ingestion_auth_missing():
    response = client.get("/test/ingestion")
    assert response.status_code == 401


def test_ingestion_auth_invalid():
    response = client.get(
        "/test/ingestion",
        headers={"Authorization": "Bearer wrong-token-value"},
    )
    assert response.status_code == 403


def test_ingestion_auth_valid():
    valid_token = settings.INGESTION_TOKEN.get_secret_value()
    response = client.get(
        "/test/ingestion",
        headers={"Authorization": f"Bearer {valid_token}"},
    )
    assert response.status_code == 200
    assert response.json() == {"message": "ingestion authorized"}


def test_dashboard_auth_valid():
    valid_token = settings.DASHBOARD_TOKEN.get_secret_value()
    response = client.get(
        "/test/dashboard",
        headers={"Authorization": f"Bearer {valid_token}"},
    )
    assert response.status_code == 200
    assert response.json() == {"message": "dashboard authorized"}
