from setuptools import setup

setup(
    name='quasselflask',
    version='0.1',
    packages=['quasselflask'],
    url='https://github.com/Laogeodritt/quasselflask',
    license='GPLv3',
    author='Marc-Alexandre Chan',
    author_email='marcalexc@arenthil.net',
    setup_requires=['Flask>=0.10',
                    'Flask-User>=0.6.8',
                    'SQLAlchemy>=0.9.1',
                    'Flask-SQLAlchemy>=1.0',
                    'psycopg2',  # PostgreSQL
                    'crcmod>=1.7'
                    ],
    include_package_data=True,
    zip_safe=False,
    description='A web-based search utility for IRC logs stored by the Quassel client (postgresql only).',
    long_description='A web-based search utility for IRC logs stored by the Quassel client (postgresql only).'
)

