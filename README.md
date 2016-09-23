# Introduction

**Quasselflask** is a web application intended to facilitate searching and exporting IRC logs stored by the [quassel IRC client](http://quassel-irc.org/) written in Python and making use of Flask, SQLAlchemy and JQuery.

The features supported:

(**WARNING**: This software is in early development, so only some of these features are functional. It's not ready for general use. Curious where things are? Feel free to contact me.)

* Searching quassel logs via network, channel, usermask, date/time range, keywords (boolean search)
* User management: protects logs from public access via username/password. Optionally, limit the channels that can be searched by each user (does not integrate with quassel's users)
* Text and HTML export of results
* Support for IRC formatting and colours and nickname colours
* Context expansion of search results
* Default CSS colour scheme available in your choice of [Solarized](http://ethanschoonover.com/solarized) Light or Dark =\] (I know some are less fond of it, but I personally love this colour palette!)

A lot of its power is derived from a need, in medium to large IRC communities, for the ops to investigate reports of events happening in the past and to save records or distribute them to other ops. (Admittedly, a lot of it is just because I can and it's fun, too!)

# A note on public logging

**Important**:

This application is meant for *personal* use. Please do not use it for the purpose of making your logs available to the public at large ("public logging").

Many channels do not allow public logging. Even if it is not expressly disallowed, public logging is generally looked down upon, as it fails to respect user privacy (even for public channels&mdash;in the same way that you might not want your conversations in public to be recorded and made available to everyone).

**If someone is making your channel's logs public using Quasselflask**: Please be aware that I am only the developer of this software, and it is freely available for anyone to use. *I do not provide hosting services*: this means I don't know *who* is using it and *how*, nor can I do anything about it. If you have concerns about a specific server running this software, I recommend you contact the owner or administrator of that server (or their hosting company).

# Configuration

To configure Quasselflask, you should make a directory (preferably outside the quasselflask directory) and create a new file called `quasselflask.cfg`.

When you run Quasselflask (see *Installation and running*, below), make sure that the environment variable `QF_CONFIG_PATH` is set set to the directory where you created the `quasselflask.cfg` file. This goes for running it using the test server as much as deploying it via WSGI in Apache, etc. (described below).

Here is a basic example configuration file that is enough to get you up and running:

    SQLALCHEMY_DATABASE_URI = 'postgresql://sqluser:password@hostname-or-IP-address/databasename'
    SITE_NAME = "John's IRC Logs"

The first line `SQLALCHEMY_DATABASE_URI` tells Quasselflask which database to connect to. At this time, only the PostgreSQL backend is supported[1]. The example is self-explanatory, but here is documentation if needed: [SQLAlchemy Database URLs](http://docs.sqlalchemy.org/en/latest/core/engines.html#postgresql).

The second line `SITE_NAME` refers to the name that will be shown in the tab title and as a heading at the top of each page. It is purely aesthetic.

You can find out about other configuration variables by checking out [quasselflask/core.py](quasselflask/core.py) - scroll down to the `class DefaultConfig:` line. Each line underneath that one is a configuration variable you can change by copying it into your `quasselflask.cfg` file and modifying the value; the comment after the `#` is an explanation (you can remove this).

This software is still under development and the configuration is changing as I develop it, so I have not yet documented configuration more robustly.

**TODO:** Document individual variables.

[1] SQLite support is not possible because it does not allow concurrency (multiple applications to open the database at once). However, it might be possible if you were to make a copy of the SQLite database for Quasselflask to use. You can try getting this to work at your own risk.

# Requirements

This application requires:

* Python 3. Tested against Python 3.5.2; should work for Python 3.x in general, but I'm not sure. (If you've discovered it doesn't work for some versions, please let me know!)
* If you are using a Python version *earlier* than 3.4, you need to [install setuptools and pip](https://packaging.python.org/installing/#requirements-for-installing-packages)
* `libpq` library and the `pg_config` tool. On Debian and Ubuntu, run `sudo apt-get install libpq-dev`. On other Linux distros, try and find `libpq-dev`, `postgresql-devel` or a similar package. On Windows

You don't need to install other dependencies yourself. The setup.py will do it for you!

If you're curious about dependencies, check out the [setup.py](setup.py) file, specifically the `setup_requires` parameter.

# Preparing the database

In order to use Quasselflask, you need to prepare the database and database server. This should not affect Quassel's operation at all nor change your data. However, **you should always keep backups in case something happens**. Things can go wrong.

We need to do two things: create a postgresql user with appropriate permissions permissions; and
 
 The instructions below assume you are root on a Linux system with postgresql; **or** that you have shell access to the Linux system running postgresql, and you can use the `psql` utility with sufficient permissions to manage users and your Quassel database.

If you have a control panel or something else to manage your postgresql database, then you should find out how to do the below steps using your system.

## Creating the database user

**TODO:** this section

## Creating indexes to speed up searching

**TODO:** finish this section: add indices in the `backlog` table to the `senderid` and `time` columns.

This is an important step, because Quassel doesn't use the database to do deep searching, and there doesn't set up the database to be able to do this quickly. The following steps will create indices on a few columns to speed up searches&mdash;this will not change anything for Quassel's operation, but it will make your database take up a little bit more disk space.

As a point of comparison: without doing this, searches took 15-20 seconds (ridiculous!). After doing this, the same test searches took around 0.2-0.6 seconds, with some of them taking up to 4s (didn't quite understand why so long!).


# Installation and running

We recommend using a virtualenv to set up Quasselflask. This is a standard Python tool and I will assume you know how to use it; if you are new to Python, you can read the [Flask docs on virtualenv and installing Flask](http://flask.pocoo.org/docs/0.11/installation/) to get a basic introduction.

You do not need to install dependencies manually. Quasselflask comes ready as a package, so you can simply run the `setup.py` file. Assuming you created your virtualenv in the directory `./venv` and you downloaded Quasselflask to `./quasselflask`, you need to do the following in a terminal window:

1. Activate the virtualenv:

       ./venv/bin/activate

2. Run the setup.py file.

The application is a fairly simple Flask application. As such, you can run it in the normal ways that you would run a Flask application:

* For testing it out or using it locally,
* [Flask deployment options](http://flask.pocoo.org/docs/0.11/deploying/), for a publicly hosted website. (This doesn't mean the logs are public, since you still have to login with a username/password to search them.)

# API

## /search

**Methods** GET

**Requires login** Yes

**Description** Searches IRC logs according to query parameters. If no parameters given, shows the blank search form.

The query parameters are better described in the help text [on the search page](quasselflask/templates/search_form.html).

Wildcards: You can use `*` (zero or more characters), `?` (one character), and `\*` or `\?` to search for a literal asterisk or question mark.

Response format: Web page (HTML). Web page with results (most recent first).

URI structure:

* `/search`

Query parameters (all optional):

* `channel`: space-separated list of channels. Accepts wildcards. (Make sure to URL-encode this if you're writing it by hand - in particular, `#` is encoded as `%23`).
* `usermask`: space-separated list of usermasks. Accepts wildcards.
* `start`: Earliest timestamp to search, in `YYYY-MM-DD HH:MM:SS.SSS` format (24-hour format). Uses the timezone of the stored quassel logs (timezone of the server).
* `end`: Latest timestamp to search. Same format as `start`.
* `limit`: Max number of results to return.
* `query`: Literal text query. Supports boolean searches (AND, OR, parentheses, quotation marks) and optionally wildcards.
* `query_wildcard`: If value is `1`, enables wildcards on the `query` parameter. If not passed or value `0`, disables wildcards. Be careful about making complex searches with wildcards, as it can be resource-intensive on the database.


# Features todo
* quasseluser/network search criteria
* User login and user/network/channel limitations
* IRC formatting (bold, italics, colours, etc.)
* Username colours
* Context up/down + amount of context to fetch
* Search by type of message (message, join, part, mode changes, etc.)
* Pagination
* Text export
* Server configuration
* PM search

# Things to document
* QF_ALLOW_TEST_PAGES
* User:

      \connect quasseldb
      CREATE USER quasselflask WITH NOSUPERUSER NOCREATEDB NOCREATEROLE NOCREATEUSER NOINHERIT LOGIN NOREPLICATION ENCRYPTED PASSWORD 'yourpasswordhere';
      REVOKE ALL ON DATABASE quasseldb FROM quasselflask;
      REVOKE ALL ON ALL TABLES IN SCHEMA public FROM quasselflask;
      GRANT CONNECT ON DATABASE quasseldb TO quasselflask;
      GRANT SELECT ON ALL TABLES IN SCHEMA public TO quasselflask;
      # TODO: add stuff for the user tables
