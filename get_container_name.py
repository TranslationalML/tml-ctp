# Copyright 2023-2024 Lausanne University and Lausanne University Hospital, Switzerland & Contributors

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from tml_ctp.info import __container_name__


def main():
    """Returns the container name of the package."""
    print(__container_name__)
    return __container_name__


if __name__ == "__main__":
    main()