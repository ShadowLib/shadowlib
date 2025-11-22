"""Tests for the QueryBuilder class."""

from shadowlib._internal.query import QueryBuilder


class TestQueryBuilder:
    """Test suite for QueryBuilder class."""

    def testQueryBuilderInitialization(self):
        """Test that query builder initializes properly."""
        qb = QueryBuilder()
        assert qb is not None

    def testQueryBuilderFilter(self):
        """Test adding filters to query builder."""
        qb = QueryBuilder()
        result = qb.filter("name", "test")
        assert result is qb  # Test method chaining

    def testQueryBuilderReset(self):
        """Test resetting query builder."""
        qb = QueryBuilder()
        qb.filter("name", "test")
        result = qb.reset()
        assert result is qb  # Test method chaining

    def testQueryBuilderExecute(self):
        """Test executing a query."""
        qb = QueryBuilder()
        qb.filter("name", "test")
        results = qb.execute()
        assert isinstance(results, list)
