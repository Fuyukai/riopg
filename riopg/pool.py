# This file is part of riopg.
#
# riopg is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# riopg is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with riopg.  If not, see <http://www.gnu.org/licenses/>.
"""
.. currentmodule:: riopg.pool
"""
import collections
from typing import Callable

import multio

from riopg import connection as md_connection


async def create_pool(dsn: str, pool_size: int = 12, *,
                      connection_factory: 'Callable[[], md_connection.Connection]' = None) \
        -> 'Pool':
    """
    Creates a new :class:`.Pool`.

    :param dsn: The DSN to connect to the database with.
    :param pool_size: The number of connections to hold at any time.
    :param connection_factory: The pool factory callable to use to
    :return: A new :class:`.Pool`.
    """
    pool = Pool(dsn, pool_size, connection_factory=connection_factory)
    return pool


class _PoolConnectionAcquirer:
    """
    A helper class that allows doing ``async with pool.acquire()``.
    """

    def __init__(self, pool: 'Pool'):
        """
        :param pool: The :class:`.Pool` to use.
        """
        self._pool = pool
        self._conn = None

    async def __aenter__(self) -> 'md_connection.Connection':
        self._conn = await self._pool._acquire()
        return self._conn

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._pool.release(self._conn)
        return False

    def __await__(self):
        return self._pool._acquire().__await__()


class Pool(object):
    """
    Represents a pool of connections.
    """

    def __init__(self, dsn: str, pool_size: int = 12, *,
                 connection_factory: 'Callable[[], md_connection.Connection]' = None):
        self.dsn = dsn
        self._pool_size = pool_size
        self._connection_factory = connection_factory or md_connection.Connection.open

        self._sema = multio.Semaphore(pool_size)
        self._connections = collections.deque()
        self._closed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
        return False

    async def _make_new_connection(self) -> 'md_connection.Connection':
        """
        Makes a new connection.

        :return: A new :class:`.Connection` or subclass of.
        """
        conn = await self._connection_factory(self.dsn)
        return conn

    async def _acquire(self) -> 'md_connection.Connection':
        """
        Acquires a new connection.

        :return: A :class:`.Connection` from the pool.
        """
        # wait for a new connection to be added
        await self._sema.acquire()
        try:
            conn = self._connections.popleft()
        except IndexError:
            conn = await self._make_new_connection()

        return conn

    def acquire(self) -> '_PoolConnectionAcquirer':
        """
        Acquires a connection from the pool. This returns an object that can be used with
        ``async with`` to automatically release it when done.
        """
        if self._closed:
            raise RuntimeError("The pool is closed")

        return _PoolConnectionAcquirer(self)

    async def release(self, conn: 'md_connection.Connection'):
        """
        Releases a connection.

        :param conn: The :class:`.Connection` to release back to the connection pool.
        """
        if conn is None:
            raise ValueError("Connection cannot be none")

        await multio._maybe_await(self._sema.release())

        if conn._connection.closed:
            # thanks a lot
            return

        self._connections.append(conn)

    async def close(self):
        """
        Closes this pool.
        """
        for connection in self._connections:
            await connection.close()

        self._closed = True
