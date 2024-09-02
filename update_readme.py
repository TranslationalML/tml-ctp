# Copyright 2023-2024 Lausanne University and Lausanne University Hospital, Switzerland & Contributors

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Module to update versions in README.md"""

import re
import requests


def get_pypi_version(package_name):
    """Fetches the latest version of a Python package from PyPI.

    Args:
        package_name (str): The name of the package on PyPI.

    Returns:
        str: The latest version of the package.

    Raises:
        Exception: If the request to PyPI fails.
    """
    url = f"https://pypi.org/pypi/{package_name}/json"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return data["info"]["version"]
    else:
        raise Exception(f"Failed to fetch version from PyPI for {package_name}")


def get_quayio_tag(repository_name):
    """Fetches the latest version tag for a Docker image from Quay.io.

    Args:
        repository_name (str): The name of the repository on Quay.io.

    Returns:
        str: The latest versioned tag of the Docker image.

    Raises:
        Exception: If the request to Quay.io fails or if no versioned tags are found.
    """
    url = f"https://quay.io/api/v1/repository/{repository_name}/tag/?onlyActiveTags=true"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        tags = data.get("tags", [])

        if isinstance(tags, list):
            # Filter tags that match the version pattern X.Y.Z
            versioned_tags = [tag for tag in tags if re.match(r'^\d+\.\d+\.\d+$', tag["name"])]

            if not versioned_tags:
                raise Exception("No versioned tags found")

            # Find the tag with the most recent last_modified date among versioned tags
            latest_tag = max(versioned_tags, key=lambda tag: tag["last_modified"])
            return latest_tag["name"]  # Return the name of the latest versioned tag
        else:
            raise Exception("Unexpected tags format received from Quay.io")
    else:
        raise Exception(f"Failed to fetch tags from Quay.io for {repository_name}")


def update_readme(pypi_version, quayio_tag):
    """Updates the README.md file with the latest PyPI and Quay.io versions.

    Args:
        pypi_version (str): The latest version of the package on PyPI.
        quayio_tag (str): The latest versioned tag of the Docker image on Quay.io.
    """
    with open("README.md", "r") as file:
        readme = file.read()

    # Update the Docker pull command
    readme = re.sub(r'docker pull quay.io/translationalml/tml-ctp-anonymizer:\d+\.\d+\.\d+', f'docker pull quay.io/translationalml/tml-ctp-anonymizer:{quayio_tag}', readme)

    # Update the pip install command
    readme = re.sub(r'pip install tml_ctp==\d+\.\d+\.\d+', f'pip install tml_ctp=={pypi_version}', readme)

    # The last update is removed since there's no version to replace

    with open("README.md", "w") as file:
        file.write(readme)


def main():
    package_name = "tml_ctp"
    repository_name = "translationalml/tml-ctp-anonymizer"

    pypi_version = get_pypi_version(package_name)
    quayio_tag = get_quayio_tag(repository_name)

    update_readme(pypi_version, quayio_tag)
    print(f"Updated README.md with PyPI version {pypi_version} and Quay.io tag {quayio_tag}")


if __name__ == "__main__":
    main()
