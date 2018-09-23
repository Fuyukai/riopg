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
.. currentmodule:: riopg.connection
"""

import socket

import inspect
import multio
from psycopg2 import OperationalError, connect
from psycopg2._psycopg import connection
from psycopg2.extensions import POLL_ERROR, POLL_OK, POLL_READ, POLL_WRITE

from riopg import cursor as md_cursor


class Connection(object):
    """
    Wraps a :class:`psycopg2.Connection` object, making it work with an async library.

    Do not construct this object manually; use :meth:`.Connection.open` or :meth:`.Pool.acquire`.
    """

    def __init__(self):
        #: The actual connection object being used.
        self._connection = None  # type: connection

        #: The connection socket being used.
        self._sock = None  # type: socket.socket

        #: The current connection lock. This prevents multiple cursors from executing at the same
        #: time.
        self._lock = multio.Lock()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
        return False

    # catch-all handler
    def __getattr__(self, item):
        original = getattr(self._connection, item)
        if not callable(original):
            return original

        # wrap in a _do_async
        def wrapper(s, fn):
            def wrapped(*args, **kwargs):
                return s._do_async(fn, *args, **kwargs)

            return wrapped
        return wrapper(self, original)

    @classmethod
    async def open(cls, *args, **kwargs) -> 'Connection':
        """
        Opens a new connection.
        """
        conn = cls()
        await conn._connect(*args, **kwargs)
        return conn

    async def _wait_callback(self):
        """
        The wait callback. This callback is used for polling the psycopg2 sockets, waiting until
        they are ready.
        """
        while True:
            state = self._connection.poll()
            if state == POLL_OK:
                return

            elif state == POLL_READ:
                await multio.asynclib.wait_read(self._sock)

            elif state == POLL_WRITE:
                await multio.asynclib.wait_write(self._sock)

            elif state == POLL_ERROR:
                raise OperationalError("Polling socket returned error")

    async def _do_async(self, fn, *args):
        """
        Performs a psycopg2 action asynchronously, using the wait callback.
        """
        async with self._lock:
            res = fn(*args)
            if inspect.isawaitable(res):
                res = await res

            await self._wait_callback()  # performs any outstanding network read/writes

        return res

    async def _connect(self, dsn: str):
        """
        Connects the psycopg2 connection.

        :param dsn: The DSN to connect with.
        """
        self._connection = connect(dsn, async_=True)
        # the socket is required for trio to eat
        # TODO: not AF_INET
        self._sock = socket.fromfd(self._connection.fileno(), socket.AF_INET, socket.SOCK_STREAM)
        await self._wait_callback()

    def _cursor(self, **kwargs):
        """
        Internal implementation of acquiring a cursor.
        """
        return self._connection.cursor(**kwargs)

    async def cursor(self, **kwargs) -> 'md_cursor.Cursor':
        """
        Gets a new cursor object.

        :return: A :class:`.cursor.Cursor` object attached to this connection.
        """
        cur = md_cursor.Cursor(self, kwargs)
        await cur.open()
        return cur

    async def close(self):
        """
        Closes this connection.
        """
        self._connection.close()  # can't do this async - raises an interfaceerror...
