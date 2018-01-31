import os
from setuptools import setup

from trifeni import __version__

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = "trifeni",
    version = __version__,
    author = "Dean Shaff",
    author_email = "dean.shaff@gmail.com",
    description = ("Access Pyro objects that are located on arbitrary remote machines"),
    install_requires=[
        'Pyro4', 'paramiko'
    ],
    packages=["trifeni"],
    keywords = ["pyro4","tunneling","ssh tunneling"],
    url = "https://github.com/dean-shaff/pyro4tunneling",
    data_files = [("", ["LICENSE"])]
)
