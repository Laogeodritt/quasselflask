from setuptools import setup, find_packages

setup(
    name='quasselflask',
    version='0.8.0rc1',
    packages=find_packages(),
    url='https://github.com/Laogeodritt/quasselflask',
    license='GPLv3',
    author='Marc-Alexandre Chan',
    author_email='laogeodritt@arenthil.net',
    install_requires=['Flask>=0.10',
                    'Flask-User>=0.6.8,<0.7',
                    'Flask-SQLAlchemy>=1.0',
                    'Flask-Mail>=0.9.0',  # this was just the latest at the time
                    'Flask-Script>=2.0.0',  # version? "latest" on readthedocs.io say 0.4.0... no version notations...
                    'SQLAlchemy>=1.1',
                    'psycopg2',  # PostgreSQL
                    'crcmod>=1.7',
                    'itsdangerous',
                    'pyghostlid>=0.2',
                    ],
    include_package_data=True,
    zip_safe=False,
    description='A web-based search utility for IRC logs stored by the Quassel client (postgresql only).',
    long_description='A web-based search utility for IRC logs stored by the Quassel client (postgresql only).'
)

