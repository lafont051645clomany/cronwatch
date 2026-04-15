"""Package setup for cronwatch."""

from setuptools import setup, find_packages

setup(
    name="cronwatch",
    version="0.1.0",
    description="A lightweight CLI tool to monitor cron job execution times and alert on unexpected delays or failures.",
    author="cronwatch contributors",
    python_requires=">=3.11",
    packages=find_packages(exclude=["tests*"]),
    install_requires=[
        "tomli>=2.0; python_version<'3.11'",
        "croniter>=1.4",
    ],
    extras_require={
        "dev": [
            "pytest>=7",
            "pytest-cov",
        ]
    },
    entry_points={
        "console_scripts": [
            "cronwatch=cronwatch.cli:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Environment :: Console",
        "Topic :: System :: Monitoring",
    ],
)
