from setuptools import setup, find_packages

requirements = [
    "requests",
    "websocket-client==1.3.1", 
    "setuptools", 
    "json_minify", 
    "six",
    "aiohttp",
    "websockets"
]

with open("README.md", "r") as stream:
    long_description = stream.read()

setup(
    name="amino.dorks.fix",
    license="MIT",
    author="misterio",
    version="1.0.0",
    author_email="misterio1234321@gmail.com",
    description="Library for Amino. Telegram - https://t.me/aminodorks",
    url="https://github.com/misterio060/amino.dorks.fix",
    packages=find_packages(),
    long_description=long_description,
    install_requires=requirements,
    keywords=[
        'aminoapps',
        'amino.fix',
        'amino',
        'aminodorks',
        'amino-bot',
        'narvii',
        'api',
        'python',
        'python3',
        'python3.x',
        'misterio060'
    ],
    python_requires='>=3.6',
)
