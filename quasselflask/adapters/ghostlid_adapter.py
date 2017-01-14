"""
Adapter for ghostlid. Configures ghostlid from flask config.

Project: Quasselflask
"""

from ghostlid import GhostLid

from quasselflask import app, __version__

ghostlid = GhostLid(
    host=app.config.get('QF_GHOSTBIN_HOST'),
    user_agent=app.config.get('QF_GHOSTBIN_HOST').format(version=__version__),
    defaults={
        'lang': 'irc',
        'expire': '10m',
        'password': None
    }
)
ghostlid.load_languages()
