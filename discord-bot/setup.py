from setuptools import setup, find_packages

setup(
    name="WickedWhiskers",
    version="1.0.0",
    description="A Halloween-themed Discord bot for managing candy games.",
    author="doodlebunnyhops",
    author_email="your-email@example.com",  # Replace with your actual email
    packages=find_packages(),  # Automatically find any Python packages in the project
    install_requires=[
        "discord.py==2.3.2",
        "aiosqlite==0.17.0",  # Async SQLite for database
        "asyncio==3.4.3",
        "PyYAML==6.0",  # Optional if you use YAML
    ],
    python_requires='>=3.8',  # Specify the required Python version
    classifiers=[
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: MIT License",  # Specify license
        "Operating System :: OS Independent",
    ],
    entry_points={
        'console_scripts': [
            'candy-bot=bot.main:run',  # Assuming your bot entry point is in bot/main.py with a run() function
        ]
    }
)
