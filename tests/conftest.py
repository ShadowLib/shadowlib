"""Pytest configuration and fixtures."""

import pytest

from shadowlib.client import Client


@pytest.fixture
def client():
    """
    Provide a Client instance for testing.

    Returns:
        Client: A fresh client instance
    """
    return Client()


@pytest.fixture
def connectedClient(client):
    """
    Provide a connected Client instance.

    Args:
        client: Client fixture

    Returns:
        Client: A connected client instance
    """
    client.connect()
    yield client
    client.disconnect()
