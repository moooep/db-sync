from setuptools import setup, find_packages

setup(
    name="db-sync",
    version="1.0.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "flask",
        "flask-socketio",
        "python-socketio",
        "eventlet",
        "configparser",
    ],
    author="Your Name",
    author_email="your.email@example.com",
    description="SQLite Database Synchronization Tool",
    keywords="sqlite, database, synchronization",
    url="https://github.com/yourusername/db-sync",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Web Environment",
        "Framework :: Flask",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Topic :: Database",
    ],
) 