import os
from setuptools import setup

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = "pyro4tunneling",
    version = "0.1.0",
    author = "Dean Shaff",
    author_email = "dean.shaff@gmail.com",
    description = ("Access Pyro objects that are located on arbitrary remote machines"),
    install_requires=[
        'Pyro4'
    ],
    packages=["pyro4tunneling"],
    keywords = ["pyro4","tunneling"],
    url = "https://github.com/dean-shaff/pyro4tunneling",
    data_files = [("", ["LICENSE"])]
)
