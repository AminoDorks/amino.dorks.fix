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

with open("README.md", "r", encoding="utf-8") as stream:
    long_description = stream.read()

setup(
    name="amino.dorks.fix",
    version="3.3.6.2",
    author="misterio",
    author_email="misterio1234321@gmail.com",
    description="Library for Amino. Telegram - https://t.me/aminodorks",
    long_description=long_description,
    long_description_content_type="text/markdown",  # важно для PyPI
    url="https://github.com/misterio060/amino.dorks.fix",
    packages=find_packages(),
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
    license="MIT",
)
