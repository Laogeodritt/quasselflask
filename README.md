# Introduction

**Quasselflask** is a web application intended to facilitate searching and exporting IRC logs stored by the [quassel IRC client](http://quassel-irc.org/) written in Python and making use of Flask, SQLAlchemy and JQuery.

Quasselflask runs wherever Python + Flask run (Linux, Mac OSX, Windows users, y'all good). Note, however, that documentation is primarily written for Linux and assumes you have some basic Linux/Python knowledge. I know that this is sub-optimal, but writing good documentation takes a lot of time (and I don't have access to Mac OSX). I'd be very appreciative of documentation additions and improvements.

The features supported:

(**WARNING**: This software is in early development, so only some of these features are functional. It's not ready for general use. Curious where things are? See the GitHub Issue tracke or feel free to contact me.)

* Search quassel logs via network, channel, usermask, date/time range, keywords (boolean search)
* Display a summary of nicknames and usermasks for a given search
* User management: protect logs from public access via username/password. Optionally, limit the channels that can be searched by each user (does not integrate with quassel's users - manual association)
* Support for showing IRC formatting and colours
* Support for nickname colours (hash method matches Quassel)
* Text export of results with auto-pastebin for sharing
* Context expansion of search results
* Default CSS colour scheme available in your choice of [Solarized](http://ethanschoonover.com/solarized) Light or Dark =\] (I know some are less fond of it, but I personally love this colour palette!)

A lot of its power is derived from a need, in medium to large IRC communities, for the ops to investigate reports of events happening in the past and to save records or distribute them to other ops. (Admittedly, a lot of it is just because I can and it's fun, too!)

# A note on public logging

**Important**:

This application is meant for *personal* use. Please do not use it for the purpose of making your logs available to the public at large ("public logging").

Many channels do not allow public logging. Even if it is not expressly disallowed, public logging is generally looked down upon, as it fails to respect user privacy (even for public channels&mdash;in the same way that you might not want your conversations in public to be recorded and made available to everyone, even if you're OK having them in public).

**If someone is making your channel's logs public using Quasselflask**: Please be aware that I am only the developer of this software, and it is freely available for anyone to use. *I do not provide hosting services*: this means I don't know *who* is using it and *how*, nor can I do anything about it. If you have concerns about a specific server running this software, I recommend you contact the owner or administrator of that server (or their hosting company).

# Configuration

You need to create a configuration file called `quasselflask.cfg` in the Flask instance path directory.

The default location is in `$PREFIX/var/quasselflask-instance` (where `$PREFIX` is the location of your virtualenv if you're using that, or probably `/usr` if you installed it system-wide - see *Installation and running*, below).

If you want to change the location: when you run Quasselflask, you can set the `QF_CONFIG_PATH` environment variable to the directory containing your `quasselflask.cfg` file. This goes for command-line maintenance commands and running it using the test server as much as deploying it via WSGI in Apache, etc.

Here is a basic example configuration file that is enough to get you up and running (**TODO: update this** - for now scroll down for a link to `base_config.py` for more up-to-date info):

    SQLALCHEMY_DATABASE_URI = 'postgresql://sqluser:password@hostname-or-IP-address/databasename'
    SITE_NAME = "John's IRC Logs"
    SECRET_KEY = 'A totally random string here - important for security!'

The first line `SQLALCHEMY_DATABASE_URI` tells Quasselflask which database to connect to. At this time, only the PostgreSQL backend is supported[1]. The example is self-explanatory, but here is documentation if needed: [SQLAlchemy Database URLs](http://docs.sqlalchemy.org/en/latest/core/engines.html#postgresql).

The second line `SITE_NAME` refers to the name that will be shown in the tab title and as a heading at the top of each page. It is purely aesthetic.

The third line `SECRET_KEY` is important for the security of passwords and other hashed items. It is very important you use a long, random string.

You can use the following in Python (Linux only?) to generate a secret key to copy-and-paste into your config file:

    >>> import os
    >>> os.urandom(24)
    '\xfd{H\xe5<\x95\xf9\xe3\x96.5\xd1\x01O<!\xd5\xa2\xa0\x9fR"\xa1\xa8'

The third line will change randomly and is a good secret key (see also [Flask Quickstart: Sessions](http://flask.pocoo.org/docs/0.11/quickstart/#sessions)). Alternatively, you could use [Random.org's string service](www.random.org/strings) (in this case, make it at least 28 characters with uppercase/lowercase letters and numbers all enabled.)

You can find out about other configuration variables by checking out [quasselflask/base_config.py](quasselflask/base_config.py) - scroll down to the `class DefaultConfig:` line. Each line underneath that one is a configuration variable you can change by copying it into your `quasselflask.cfg` file and modifying the value; the comment after the `#` is an explanation (you can remove this). Do not use any configuration variables under `InternalConfig` unless you're sure of what you're doing!

This software is still under development and the configuration is changing as I develop it, so I have not yet documented configuration more robustly.

**TODO:** Document individual variables.

[1] SQLite support is not possible because it does not allow concurrency (multiple applications to open the database at once). Some database engine features used in searching and quasselflask user management may be unavailable in SQLite (haven't scrutinised features thoroughly since I wrote it against postgresql specifically).

# Requirements

This application requires:

* quasselcore - must be running on the PostgreSQL backend (SQLite backend not supported).
* PostgreSQL >= 9.1 (I think - a version that supports  GIN/GIST trigram indices for LIKE/ILIKE).
* Python 3.x - tested against 3.5.2 only. (If you've discovered it doesn't work for some versions, please let me know!)
  * If using Python <= 3.4, also install [ setuptools and pip](https://packaging.python.org/installing/#requirements-for-installing-packages).
* `libpq` library for the `pg_config` tool.
  * Debian, Ubuntu, etc.: run `sudo apt-get install libpq-dev`
  * Other Linux: Try and find a package called `libpq-dev`, `postgresql-devel` or similar.
  * Windows: Should not be needed.
* `libffi-dev` for some headers required by Python packages (Linux only?).

You don't need to install other dependencies yourself. The setup.py will do it for you!

If you're curious about dependencies, check out the [setup.py](setup.py) file, specifically the `setup_requires` parameter.

# Preparing the database

In order to use Quasselflask, you need to prepare the database and database server. This should not affect Quassel's operation at all nor change your data. However, **you should always keep backups in case something happens**. Things can go wrong.

We need to do a couple things to prepare everything. Some things are specific to your database and must be done using your own tools (manually or using any tools you already use for postgresql if you're a sysadmin); others can be done automatically through a QuasselFlask command.

Specifically, we will need to:

1. Create a postgreSQL user with the appropriate permissions, so QuasselFlask can log into the server;
2. Enable the PostgreSQL trigram extension, used for creating searchable indices;
3. *Later*, after installing Quasselflask, create the indices in the database that speed up Quasselflask searches (quassel itself never searches using these criteria, so it doesn't make these particular indices);
4. *Later*, after installing Quasselflask, set up the Quasselflask tables and initial user.

 The instructions below assume you are root on a Linux system with postgresql; **or** that you have shell access to the Linux system running postgresql, and you can use the `psql` utility with sufficient permissions to manage users and your Quassel database.

If you have a control panel or something else to manage your postgresql database, then you should find out how to do the below steps using your system.

## Creating the database user

First, in a terminal, run the `psql` utility as the PostgreSQL superuser and connect to your Quassel database(`postgres` is the default PostgreSQL superuser on Debian, Ubuntu and other Debian-based distros; other distros may vary; `quasseldb` is the name of *your* Quassel database which you should change accordingly):

    sudo -u postgres psql quasseldb

Then type in this command to create a user specifically for Quasselflask (replace `quasselflask` with a different username if desired; and replace `yourpasswordhere` with your password):

    CREATE USER quasselflask WITH NOSUPERUSER NOCREATEDB NOCREATEROLE NOCREATEUSER NOINHERIT LOGIN NOREPLICATION ENCRYPTED PASSWORD 'yourpasswordhere';

Set up the user's permissions:

    REVOKE ALL ON DATABASE quasseldb FROM username;
    REVOKE ALL ON ALL TABLES IN SCHEMA public FROM quasselflask;
    REVOKE ALL ON SCHEMA public FROM quasselflask;
    GRANT CONNECT, CREATE ON DATABASE quasseldb TO quasselflask;
    GRANT ALL ON SCHEMA public TO quasselflask;
    GRANT SELECT, REFERENCES ON ALL TABLES IN SCHEMA public TO quasselflask;

The last line is selected as such for security: this prevents Quasselflask from editing Quassel's tables (e.g. in case of a compromise of Quasselflask or of the SQL user it's using). This does add a few more steps to setup; if the security problem with this isn't a concern to you, you could change it to `GRANT ALL ON ALL TABLES ...` for the last line.

Leave `psql` open for the next step.

## Enable trigram indices

This feature isn't enabled by default, but it helps us create indices that speed up searching considerably. This is a required step for the indices to be created later.

To enable the trigram extension, in `psql`, type:

    CREATE EXTENSION pg_trgm;

That's it! To exit:

    \quit

## Creating indexes to speed up searching

*This step has been automated and will be done by calling a Quasselflask command after installation, below. The below text explains the what and why.*

This is an important step, because Quassel doesn't use the database to do deep searching, and therefore doesn't set up the database to be able to do this quickly. The following steps will create indices on a few columns to speed up searches&mdash;this will not change anything for Quassel's operation, but it will make your database take up a little bit more disk space.

As a point of comparison: without doing this, searches took 15-20 seconds (ridiculous!). After doing this, the same test searches took around 0.2-0.6 seconds.

Note that this will increase the size of your database. On my test database (~600MB backlog of actual IRC backlogs), I found that the indices add about 60% of the size of the `backlog` table plus 100% of the `sender` and `buffer` tables to the total datbase size.

# Installing quasselflask

We recommend using a virtualenv to set up Quasselflask. This is a standard Python tool and I will assume you know how to use it; if you are new to Python, you can read the [Flask docs on virtualenv and installing Flask](http://flask.pocoo.org/docs/0.11/installation/) to get a basic introduction.

You do not need to install dependencies manually. Quasselflask comes ready as a package, so you can simply run the `setup.py` file. Assuming you created your virtualenv in the directory `./venv` and you downloaded Quasselflask to `./quasselflask`, you need to do the following in a terminal window:

The following instructions assume you have the following directory structure: your current directory contains subdirectory `venv` containing your virtualenv, and `quasselflask` containing a copy of Quasselflask (cloned from github or untarred).

**Reminder**: If you use a custom config file location, remember to set the `QF_CONFIG_PATH` environment variable. How to do so depends on your choice of shell.

1. Activate the virtualenv in a terminal window. For the rest of these instructions, you will run all commands in the same window that you activated the virtualenv in.

       ./venv/bin/activate

2. Run the setup.py file to install Quasselflask into your virtualenv:

        python quasselflask/setup.py

3. Place your `quasselflask.cfg` config file into `lib/quasselflask-instance/` or a custom location (see *Configuration* above).

4. Create an initial Quasselflask superuser (a.k.a. admin user). This will automatically make Quasselflask tables if needed.

        python -m quasselflask.run create_superuser username user@domain.com
    
    This will prompt you for a password. Type it in and press Enter (nothing will show up in the window).

5. Creates the indices to be used by Quasselflask for searching. Since these indices are linked to the Quasselcore tables, you need to be "owner" of the tables to do this: so you will need to modify your `quasselflask.cfg` file to use the username/password of the database user used by quasselcore (if you don't want to do this, see below for an alternative).

        python -m quasselflask.run create_indices
        
    This should automatically create the indices. Check for any error messages.
    
    Remember to revert your changes to `quasselflask.cfg`.
    
    Alternatively, you can log into `psql` again and issue these commands:
    
        CREATE INDEX qf_sender_gin_sender_idx ON sender USING gin (sender gin_trgm_ops);
        CREATE INDEX qf_buffer_gin_buffername_idx ON buffer USING gin (buffername gin_trgm_ops);
        CREATE INDEX qf_backlog_time_idx ON backlog (time);
        CREATE INDEX qf_backlog_bufferid_senderid_idx ON backlog (bufferid, senderid);
        CREATE INDEX qf_backlog_senderid_idx ON backlog (senderid);
    
6. (Optional) Now that you've created the needed database objects, you can prevent your database user from creating further tables (in case of compromise of that user or of Quasselflask). See *Creating the database user* section for a reminder of the variables you have to substitute in (we're using the same example names as in that section).

    First, at a terminal, start the `psql` utility again:

        sudo -u postgres psql quassseldb

    Then revoke the CREATE permission on the database:
    
        REVOKE CREATE ON DATABASE quasseldb TO quasselflask;
    
    And exit:
    
        \quit

# Running quasselflask

## Development mode

If you just want to run the application to test it out, to use it locally, or while developing for `quasselflask`, you can use Flask's built-in browser.

First, **a reminder** that if you use a custom location for the config file, set the `QF_CONFIG_PATH` environment variable correctly first.

1. Activate your virtualenv, if applicable (see the Installation section, header and step 1).
2. Run:

        python -m quasselflask.run runserver


## Production/deployment

If you want this to be publicly hosted, you probably want a higher-performance and more secure web server to handle the incoming requests, like nginx or Apache. Flask has good documentation for various [popular deployment options](http://flask.pocoo.org/docs/0.11/deploying/) for you to consult. ("Publicly hosted" doesn't mean the logs are public, since you still have to login with a username/password to search them.)

A sample WSGI file, `quasselflask.example.wsgi`, is provided to help you set it up; it supports a custom config file location and the use of virtualenv. You need to modify `virtualenv_dir` to specify the location of the virtualenv you're using for quasselflask, and `config_dir` for the location of the config files (if you don't want to use these features, set the value to an empty string `''`).

# Management commands

Quasselflask has a number of management commands that must be called from the command line. Make sure to activate your virtualenv first. Also make sure the environment variables needed are set (e.g. QF_CONFIG_PATH described in *Configuration* above, FLASK_DEBUG, etc.).

The general command format is:

    python -m quasselflask.run commandname [argument1 [argument2 [...]]

The available commands are `create_superuser`, `create_indices`, `reset_db`, `reset_indices`. Details are available in the application; to see the help files, run:

    python -m quasselflask.run -?

# Uninstallation

To remove QuasselFlask from your database and return it to a quasselcore-only form, first stop the Quasselflask application (this depends on how you deployed it: see Step 7 of the Installation section).

Then open a command line and activate your virtual env (see Step 1 of the Installation section).

Run these commands. **WARNING:** Although these commands aren't supposed to modify quasselcore data, using these commands is at your own risk: make sure you have database backups!

    python -m quasselflask.run reset_indices
    python -m quasselflask.run reset_db

Note that for `reset_indices`, you may have to temporarily change the database username/password to the one quasselcore is running on in your `quasselflask.cfg` file. See step 6 of the installation (create_indices step).

If you don't want to do this, you can log into `psql` and manually issue `DROP INDEX ...` commands (same commands as in the manual alternative described in the installation, but as `DROP` instead of `CREATE` commands).

(If these don't work, you may have to run `psql` and run the command `GRANT CREATE ON DATABASE quasseldb TO quasselflask`, replacing `quasseldb` with the name of your database and `quasselflask` with your database username).

Once this has been done, you can remove Quasselflask from your deployment and delete the virtual environment.


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

# Things to document
* QF_ALLOW_TEST_PAGES
* Development standard - things imported in init_app should not `from quasselflask import [...]`
* All the endpoints?
