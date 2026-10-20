import duckdb


def seed_marts(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute(
        """
        CREATE TABLE customers (
            customer_id VARCHAR,
            customer_name VARCHAR,
            count_lifetime_orders INTEGER,
            first_ordered_at TIMESTAMP,
            last_ordered_at TIMESTAMP,
            lifetime_spend DOUBLE,
            customer_type VARCHAR
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE orders (
            order_id VARCHAR,
            customer_id VARCHAR,
            ordered_at TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE order_items (
            order_item_id VARCHAR,
            order_id VARCHAR,
            product_id VARCHAR,
            product_name VARCHAR
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE products (
            product_id VARCHAR,
            product_type VARCHAR
        )
        """
    )
    conn.execute(
        """
        INSERT INTO customers VALUES
            ('c-high', 'Should Not Appear', 5, '2023-01-01', '2024-06-01', 50.0, 'returning'),
            ('c-low', 'Other', 1, '2024-01-01', '2024-01-01', 5.0, 'new')
        """
    )
    conn.execute(
        """
        INSERT INTO orders VALUES
            ('o1', 'c-high', '2024-01-01 10:00:00'),
            ('o2', 'c-high', '2024-06-01 10:00:00'),
            ('o3', 'c-low', '2024-01-01 10:00:00')
        """
    )
    conn.execute(
        """
        INSERT INTO products VALUES
            ('p-jaf', 'jaffle'),
            ('p-bev', 'beverage')
        """
    )
    conn.execute(
        """
        INSERT INTO order_items VALUES
            ('i1', 'o1', 'p-jaf', 'doctor stew'),
            ('i2', 'o2', 'p-bev', 'tangaroo'),
            ('i3', 'o3', 'p-jaf', 'mel-bun')
        """
    )
