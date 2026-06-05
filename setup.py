from setuptools import setup, find_packages

setup(
    name='minecraft_api_server',
    version='0.0.1',
    packages=find_packages(),
    install_requires=[
        "PyQt6",
        "fastapi",
        "uvicorn",
        "jinja2"
    ],
    entry_points={
        "console_scripts": [
            "minecraft_api_server=src.main:main",
        ]
    }
)