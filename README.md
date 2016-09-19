# API

## /search

Methods: GET

Requires login: Yes

Description: Searches IRC logs according to query parameters. If no parameters given, shows the blank search form.

Response format: Web page (HTML). Web page with results (most recent first).

URI structure:

* `/search`

Query parameters (all optional):

* `channel`: space-separated list of channels. (Make sure to URL-encode this - in particular, `#` is encoded as `%23`)
* `usermask`: space-separated list of usermasks; `*` may be used as a wildcard (same as in IRC ban syntax).
* `start`: Earliest timestamp to search, in `YYYY-MM-DD HH:MM:SS.SSS` format (24-hour format). Uses the timezone of the stored quassel logs (= timezone of the server, at the time of writing).
* `end`: Latest timestamp to search. Same format as `start`.
* `limit`: Max number of results to return.
* `queries`: Literal text query. Multiple copies of this variable may be present (OR'd together), and may be used in conjunction with `wildcardquery`. Multiple words are ANDed together; phrases in "quotation marks" are searched literally.
* `wildcardqueries`: Same as `query`, with the addition of the wildcards `?` to match a single character and `*` to match any number of characters.

# Features todo
* quasseluser/network searching
* User login and user/network/channel limitations
* IRC formatting
* Username colours
* Context up/down + amount of context to fetch
* Search by type of message (message, join, part, mode changes, etc.)
* Pagination
* Text export
* Server configuration
* PM search


# Things to document
* Need to add indices in the `backlog` table to the `senderid` and `time` columns.
* Also need to install "libpq-dev" (Debian/Ubuntu) package for pg_config tool  (postgresql-devel / other distros)
* SQLite not supported officially (because would need concurrent access for quassel and quasselflask).
* However possible to configure using an SQL_DATABASE_URI for SQLite (see SQLAlchemy docs), and using a COPY of the sqlite database (not the one being used by quassel). You would need to index the needed columns yourself!
* User:

      CREATE USER quasselflask WITH NOSUPERUSER NOCREATEDB NOCREATEROLE NOCREATEUSER NOINHERIT LOGIN NOREPLICATION ENCRYPTED PASSWORD 'yourpasswordhere';
      REVOKE ALL ON DATABASE quasseldb FROM quasselflask;
      REVOKE ALL ON ALL TABLES IN SCHEMA public FROM quasselflask;
      GRANT CONNECT ON DATABASE quasseldb TO quasselflask;
      GRANT SELECT ON ALL TABLES IN SCHEMA public TO quasselflask;
      # TODO: add stuff for the user tables
