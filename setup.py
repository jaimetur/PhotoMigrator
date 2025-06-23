### setup.py

import os
import re
from setuptools import setup, find_packages

# Determine the directory containing this file
here = os.path.dirname(__file__)

# 1) Read the contents of GlobalVariables.py to extract the version
version_file_path = os.path.join(here, "src", "Core", "GlobalVariables.py") # Path to the module holding the version constant
with open(version_file_path, encoding="utf-8") as f:
    file_contents = f.read()

# Use a regular expression to find SCRIPT_VERSION_WITHOUT_V
match = re.search(r"^SCRIPT_VERSION_WITHOUT_V\s*=\s*['\"]([^'\"]+)['\"]", file_contents, re.MULTILINE)
if not match:
    raise RuntimeError(
        "SCRIPT_VERSION_WITHOUT_V not found in GlobalVariables.py"
    )
version = match.group(1) # The version is captured in the first group

# 2) Read long description
readme = open(os.path.join(here, "README.md"), encoding="utf-8").read()

# 3) Read dependencies from requirements.txt if the file exists
requirements = []
requirements_path = os.path.join(here, "requirements.txt")
if os.path.isfile(requirements_path):
    with open(requirements_path, encoding="utf-8") as req_file:
        for line in req_file:
            # Skip blank lines and comments
            if line.strip() and not line.strip().startswith("#"):
                requirements.append(line.strip())

# Configure the package setup
setup(
    name="photomigrator",                           # Distribution and package name
    version=version,                                # Version read from GlobalVariables
    description="Photo Migration Tool",             # Short description
    long_description=readme,                        # Detailed description from README
    long_description_content_type="text/markdown",  # README is markdown
    package_dir={"": "src"},                        # Root of packages is src/
    packages=find_packages(where="src"),            # Automatically find all packages under src/
    install_requires=requirements,                  # Dependencies from requirements.txt
    entry_points={                                  # Define console script entry point
        "console_scripts": [
            "photomigrator = PhotoMigrator:main",
        ],
    },
    python_requires=">=3.7",                        # Minimum supported Python version
    classifiers=[                                   # Package metadata
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
