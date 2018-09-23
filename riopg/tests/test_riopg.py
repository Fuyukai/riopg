import os
import pytest

from riopg import create_pool, Connection


async def get_pool():
    return await create_pool(os.environ.get("DB_URL"))


async def get_connection():
    return await Connection.open(os.environ.get("DB_URL"))


async def test_basic_fetch():
    conn = await get_connection()
    async with conn:
        cur = await conn.cursor()
        await cur.execute("SELECT 1;")
        result = await cur.fetchone()
        assert result == (1,)

    assert conn.closed


async def test_query_param():
    conn = await get_connection()
    async with conn:
        cur = await conn.cursor()
        await cur.execute("SELECT %s", (1,))
        result = await cur.fetchone()
        assert result == (1,)


async def test_cursor():
    conn = await get_connection()
    async with conn:
        cur = await conn.cursor()
        async with cur:
            assert not cur.closed
            await cur.execute("""
            DROP TABLE IF EXISTS users;
            
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                verified BOOLEAN
            );
            INSERT INTO users VALUES (1, 'ffff', true), (2, 'gggg', false), (3, 'eeee', true);
            """)
            await cur.execute("SELECT username, verified FROM users WHERE verified = TRUE ORDER BY "
                              "id;")
            rows = await cur.fetchall()
            assert rows == [("ffff", True), ("eeee", True)]

            await cur.execute("START TRANSACTION;")
            await cur.execute("INSERT INTO users VALUES (4, 'hhhh', true)")
            await cur.execute("ROLLBACK;")
            await cur.execute("SELECT COUNT(*) FROM users;")
            assert (await cur.fetchone()) == (3,)

            await cur.execute("SELECT username FROM users ORDER BY id;")
            await cur.scroll(1)
            assert (await cur.fetchmany(2)) == [("gggg",), ("eeee",)]

            await cur.execute("SELECT * FROM users ORDER BY id;")
            counter = 0
            async for i in cur:
                assert len(i) == 3
                counter += 1

            assert counter == 3


async def test_pool():
    pool = await get_pool()
    async with pool:
        async with pool.acquire() as conn:
            cur = await conn.cursor()
            await cur.execute("SELECT 2 + 2;")
            result = await cur.fetchone()
            assert result == (4,)

        assert len(pool._connections) == 1
        async with pool.acquire() as conn2:
            assert conn2 == conn, "Connection was not reused"
            await conn2.close()

        assert len(pool._connections) == 0
        conn = await pool.acquire()
        await pool.release(conn)

    assert pool._connections[0].closed

    with pytest.raises(RuntimeError):
        await pool.acquire()
