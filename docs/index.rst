.. riopg documentation master file, created by
   sphinx-quickstart on Sun May  6 14:29:44 2018.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to riopg's documentation!
=================================

``riopg`` is a Python 3.6+ library for interfacing with `PostgreSQL`_ databases using the
`curio`_ or `trio`_ libraries.


Getting Started
---------------

To install ``riopg``, you can either install it from PyPI::

    $ pipenv install riopg

Or for the latest development version::

    $ pipenv install git+https://github.com/Fuyukai/riopg.git#egg=riopg

``riopg`` depends on multio (to provide a compatability layer between curio and trio) and
psycopg2 (to drive the connection to the database server).

Picking a Library
-----------------

In order to use ``riopg``, you must first pick an async library to use on the backend, using the
multio module.

.. code-block:: python3

    import multio
    # enable curio for this thread
    multio.init('curio')
    # or, enable trio for this thread
    multio.init('trio')

.. note::

    The choice of library is per-thread; you must call ``multio.init`` in every thread you wish
    to use async code in.

Basic Usage
-----------

The usage of ``riopg`` is intentionally designed to be similar to the psycopg2 API. To create a
connection, you can use :meth:`.Connection.open` like so:

.. code-block:: python3

    # must be called from an async context
    conn = await Connection.open("postgresql://127.0.0.1/postgres")

It is recommended you use this connection as an async context manager:

.. code-block:: python3

   async with conn:
      ...

   async with (await Connection.open(...)) as connection:
      ...

This will automatically close the connection when you are done with it.

The connection object is intentionally similar to a psycopg2 connection object. For example, to
open a cursor and perform a query:

.. code-block:: python3

    cur = await conn.cursor()
    await cur.execute("SELECT 1;")
    result = await cur.fetchone()

Like above, it is recommended to use ``async with`` with the cursor:

.. code-block:: python3

   async with (await conn.cursor()) as cursor:
      ...

Most methods on a :class:`.Connection` or a :class:`.Cursor` are wrapped in an async wrapper;
they will perform the task then automatically read/write to the socket as appropriate. No threads
are used in the operation of a connection. For example, using ``Connection.commit()`` or
``Connection.rollback()`` works automatically.

Additionally, cursors also support the async iterator protocol; you can iterate over a cursor
with ``async for``:

.. code-block:: python3

    await cur.execute("SELECT * FROM users;")
    async for item in cur:
        ...

Connection Pooling
------------------

``riopg`` also supports connection pooling with a :class:`.Pool`. To use, simply create a new
instance of ``Pool`` with :meth:`.pool.create_pool`, like so:

.. code-block:: python

    pool = await create_pool("postgresql://127.0.0.1/postgres")
    async with pool.acquire() as connection:
      ...

API Reference
-------------

.. autoclass:: riopg.connection.Connection
    :members:

.. autoclass:: riopg.cursor.Cursor
    :members:

.. autofunction:: riopg.pool.create_pool

.. autoclass:: riopg.pool.Pool
    :members:

.. _PostgreSQL: https://www.postgresql.org/
.. _curio: https://github.com/dabeaz/curio.git
.. _trio: https://github.com/dabeaz/trio.git