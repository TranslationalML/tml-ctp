#!/usr/bin/env python3

# Copyright (C) 2023, The TranslationalML team and Contributors. All rights reserved.
#  This software is distributed under the open-source Apache 2.0 license.

"""Script to delete files until a certain amount of free space is reached?

Worflow:

    1. Use `os.statvfs()` to check the free space of the given path (defaults to the current directory).
    2. Creates dummy files of size N GB until the free space drops below N+1 GB.
    3. Prompt the user to press Enter before deleting the dummy files.
    4. Delete the dummy files and show the final free space.
"""

import os


def get_free_space(path: str = "."):
    """Return the free space in bytes."""
    stat = os.statvfs(path)
    return stat.f_frsize * stat.f_bavail


def create_dummy_files(
    path: str, size: int = 15 * 1024 * 1024 * 1024, threshold: int = 16 * 1024 * 1024 * 1024
):
    """Create dummy files until free space drops below threshold."""
    dummy_files = []

    while get_free_space(path) > threshold:
        dummy_file_name = os.path.join(path, f"dummy_{len(dummy_files)}.bin")
        with open(dummy_file_name, "wb") as f:
            f.write(b"\0" * size)
        dummy_files.append(dummy_file_name)

    return dummy_files


def delete_dummy_files(dummy_files: list):
    for dummy_file in dummy_files:
        os.remove(dummy_file)


def main():
    """Main function of the `space_deleter.py` script."""
    path_to_save = "."  # current directory; adjust if needed

    print("Checking free space...")
    initial_free_space = get_free_space(path_to_save)
    print(f"Initial free space: {initial_free_space / (1024 * 1024 * 1024):.2f} GB")

    print("Creating dummy files...")
    created_files = create_dummy_files(path_to_save)
    print(f"Created {len(created_files)} dummy files.")

    input("Press Enter to delete the dummy files...")
    delete_dummy_files(created_files)
    print("Dummy files deleted.")

    final_free_space = get_free_space(path_to_save)
    print(f"Final free space: {final_free_space / (1024 * 1024 * 1024):.2f} GB")


if __name__ == "__main__":
    main()
