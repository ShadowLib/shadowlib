"""Tests for the main Client class."""

from shadowlib.client import Client


class TestClient:
    """Test suite for Client class."""

    def testClientInitialization(self):
        """Test that client initializes properly."""
        client = Client()
        assert client is not None
        assert not client.isConnected()

    def testClientConnection(self, client):
        """Test client connection."""
        assert not client.isConnected()
        result = client.connect()
        assert result is True
        assert client.isConnected()

    def testClientDisconnection(self, connectedClient):
        """Test client disconnection."""
        assert connectedClient.isConnected()
        connectedClient.disconnect()
        assert not connectedClient.isConnected()
