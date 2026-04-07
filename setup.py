"""
Setup script for MyBank
"""
from setuptools import setup, find_packages

setup(
    name='mybank',
    version='1.0.0',
    description='Telegram Bot for Online Banking',
    author='MyBank Team',
    packages=find_packages(),
    install_requires=[
        'python-telegram-bot==20.7',
        'sqlalchemy==2.0.23',
    ],
    python_requires='>=3.8',
)
