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


class Pool(object):
    """
    Represents a pool of connections.
    """

    def __init__(self, dsn: str, pool_size: int = 12, *,
                 connection_factory: 'Callable[[], md_connection.Connection]' = None):
        self.dsn = dsn
        self._pool_size = pool_size
        self._connection_factory = connection_factory or md_connection.Connection

        self._sema = multio.Semaphore(pool_size)
        self._connections = collections.deque()

    async def _make_new_connection(self) -> 'md_connection.Connection':
        """
        Makes a new connection.

        :return: A new :class:`.Connection` or subclass of.
        """
        conn = self._connection_factory()
        await conn.open(self.dsn)
        return conn

    async def acquire(self) -> 'md_connection.Connection':
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

    async def release(self, conn: 'md_connection.Connection'):
        """
        Releases a connection.

        :param conn: The :class:`.Connection` to release back to the connection pool.
        """
        await self._sema.release()
        await conn.reset()
        self._connections.append(conn)
