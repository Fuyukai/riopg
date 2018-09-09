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
.. currentmodule:: riopg.cursor
"""
from functools import partial
from psycopg2._psycopg import cursor
from typing import Any, Dict, List, Sequence, Tuple, Union

from riopg import connection as md_connection


class Cursor(object):
    """
    Wraps a :class:`psycopg2.cursor` object.
    """

    def __init__(self, connection: 'md_connection.Connection', kwargs):
        """
        :param connection: The :class:`.Connection` object this cursor was created under.
        """
        self._connection = connection
        self._kwargs = kwargs

        #: The underlying cursor object.
        self._cursor = None  # type: cursor

    async def open(self):
        """
        Opens this cursor.

        This is usually called automatically by :meth:`.Connection.open`.
        """
        self._cursor = await self._connection._do_async(partial(self._connection._cursor, **self._kwargs))

    # catch-all handler
    def __getattr__(self, item):
        original = getattr(self._cursor, item)
        if not callable(original):
            return original

        # wrap in a _do_async
        def wrapper(s, fn):
            def wrapped(*args, **kwargs):
                return s._connection._do_async(fn, *args, **kwargs)

            return wrapped
        return wrapper(self, original)

    async def __aiter__(self):
        while True:
            res = (await self.fetchone())
            if res is None:
                return

            yield res

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
        return False

    async def execute(self, sql: str, params: Union[Tuple[Any], Dict[str, Any]] = None) -> None:
        """
        Executes some SQL in this cursor.

        :param sql: The SQL to execute.
        :param params: The parameters to pass to the SQL query.
        """
        return await self._connection._do_async(partial(self._cursor.execute, sql, params))

    async def fetchone(self) -> Sequence[Any]:
        """
        Fetches one result from this cursor.

        :return: A tuple with the results of the previous query.
        """
        return await self._connection._do_async(self._cursor.fetchone)

    async def fetchmany(self, size: int = None) -> List[Sequence[Any]]:
        """
        Fetches many rows from this cursor.

        :param size: The number of rows to fetch.
        :return: A list of tuples with the results of the current query.
        """
        if size is None:
            size = self._cursor.arraysize

        return await self._connection._do_async(self._cursor.fetchmany, size)

    async def fetchall(self) -> List[Sequence[Any]]:
        """
        Fetches all the rows from this cursor.

        :return: A list of tuples with the results of the current query.
        """
        return await self._connection._do_async(self._cursor.fetchall)

    async def scroll(self, value: int, mode: str = 'relative'):
        """
        Scrolls this cursor.

        :param value: The number of rows to scroll.
        :param mode: The scroll mode to perform.
        """
        return await self._connection._do_async(self._cursor.scroll, value, mode)
