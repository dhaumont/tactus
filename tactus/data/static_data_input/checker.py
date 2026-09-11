"""Static data checker tool."""

import argparse
import json
import os
import sys
from pathlib import Path

from pathspec import PathSpec


def get_verification_key(file_path):
    """Return the key used to check file consistency."""
    return os.path.getsize(file_path)


def get_files_from_folder(folder_path, ignore_list, green_list, verbose=None):
    """Recursively get all files in folder and subfolders."""
    files = []
    seen = set()
    for root, _dirs, filenames in os.walk(folder_path, followlinks=True):
        if ignore_list and ignore_list.match_file(root):
            continue

        if verbose:
            print(root)
        ino = root
        if ino in seen:
            print(f"Warning: circular dependency detected: {root} ")
            continue
        seen.add(ino)
        for filename in filenames:
            file_path = os.path.join(root, filename)

            relative_path = os.path.relpath(file_path, folder_path)
            if ignore_list and ignore_list.match_file(relative_path):
                continue
            if green_list and not green_list.match_file(relative_path):
                continue

            file_size = os.path.getsize(file_path)
            files.append(
                {"filename": filename, "relative_path": relative_path, "size": file_size}
            )
            if verbose:
                print(f"{filename}, {file_size}")

    return files


def generate_json(folder_path, ignore_list, green_list, output_json, verbose):
    """Generate a JSON with file details."""
    files = get_files_from_folder(folder_path, ignore_list, green_list, verbose)

    data = {"folder": folder_path, "files": files}

    with open(output_json, "w") as json_file:
        json.dump(data, json_file, indent=4)

    print(f"JSON file '{output_json}' generated successfully.")


def validate_files(
    json_file, folder_path, ignore_list, green_list, verbose, cmd, scp_host, force_update
):
    """Validate files listed in the JSON."""
    with open(json_file, "r") as f:
        data = json.load(f)
    reference_folder = data["folder"]
    target_folder = folder_path

    expected_files = {f["relative_path"]: f for f in data["files"]}

    missing_files = []
    unknown_files = []
    key_mismatch = []

    # Check if files in JSON are present on disk
    for relative_path, expected in expected_files.items():
        file_path = os.path.join(folder_path, relative_path)
        if verbose:
            print(file_path)
        if not os.path.exists(file_path):
            missing_files.append(relative_path)
        else:
            # Check if the file hash matches
            actual_key = get_verification_key(file_path)
            if actual_key != expected["size"]:
                key_mismatch.append((relative_path, actual_key, expected["size"]))

    # Check if there are files on disk not listed in the JSON
    seen = set()
    for root, _dirs, filenames in os.walk(folder_path, followlinks=True):
        if ignore_list and ignore_list.match_file(root):
            continue

        if verbose:
            print(root)
        ino = root
        if ino in seen:
            print(f"# Warning: circular dependency detected: {root} ")
            continue
        seen.add(ino)

        for filename in filenames:
            relative_path = os.path.relpath(os.path.join(root, filename), folder_path)
            if ignore_list and ignore_list.match_file(relative_path):
                continue
            if green_list and not green_list.match_file(relative_path):
                continue

            if relative_path not in expected_files:
                unknown_files.append(relative_path)

    # Report results

    if missing_files:
        print(f"# Missing files ({len(missing_files)}):")
        for file in missing_files:
            if cmd:
                dir_name = os.path.dirname(f"{target_folder}/{file}")
                if scp_host:
                    print(
                        f"mkdir -p {dir_name}; scp {scp_host}:{reference_folder}/{file} \
                        {target_folder}/{file}"
                    )
                else:
                    print(
                        f"mkdir -p {dir_name}; ln -s {reference_folder}/{file} \
                        {target_folder}/{file}"
                    )

            else:
                print(f"D {file}")

    else:
        print("# No missing files.")

    if unknown_files:
        print(f"# Unknown files ({len(unknown_files)}):")
        for file in unknown_files:
            print(f"? {file}")
    else:
        print("# No unknown files.")

    if key_mismatch:
        if cmd and not force_update:
            print(
                "# Warning: files with incorrect size found, but not command \
                will be generated for them.\
                Use --force_update if you want to override them."
            )

        print(f"# Files with incorrect size ({len(key_mismatch)}):")
        for file, actual_key, expected_key in key_mismatch:
            if cmd:
                if force_update:
                    if scp_host:
                        print(
                            f"scp {scp_host}:{reference_folder}/{file} \
                            {target_folder}/{file}"
                        )
                    else:
                        print(f"cp {reference_folder}/{file} {target_folder}/{file}")
                else:
                    print(f"# Skipping - {target_folder}/{file} has inconsistent size")

            else:
                print(f"M {file} (expected: {expected_key}, found: {actual_key})")

    else:
        print("# No file with incorrect size")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="File validation script.")
    parser.add_argument("--generate", action="store_true", help="generation mode")
    parser.add_argument("--cmd", action="store_true", help="output bash copy commands")
    parser.add_argument("--folder", help="The folder to process.")
    parser.add_argument(
        "--force_update", action="store_true", help="Overwrite existing files"
    )
    parser.add_argument(
        "--ignore",
        help="Path to .ignore file to exclude files and folders.",
        default=None,
    )
    parser.add_argument(
        "--green", help="Path to .green file of allowed files and folders.", default=None
    )
    parser.add_argument("--json", help="JSON file", default=None)
    parser.add_argument("--verbose", action="store_true", help="verbose mode")
    parser.add_argument(
        "--scp_host", help="Generate scp instructions if you provide an scp host with cmd"
    )

    args = parser.parse_args()
    if not hasattr(args, "json"):
        print("Please provide a json file name")
        sys.exit(1)

    if not hasattr(args, "folder"):
        print("Please provide a folder")
        sys.exit(1)

    if args.scp_host and not args.cmd:
        print("Warning: --scp_host is ignored without the --cmd argument.")

    if args.force_update and not args.cmd:
        print("Warning: --force_update is ignored without the --cmd argument.")

    verbose = args.verbose
    ignore_list = None
    green_list = None
    if args.ignore:
        lines = Path(args.ignore).read_text().splitlines()
        ignore_list = PathSpec.from_lines("gitwildmatch", lines)

    if args.green:
        lines = Path(args.green).read_text().splitlines()
        green_list = PathSpec.from_lines("gitwildmatch", lines)

    if not args.generate:
        validate_files(
            args.json,
            args.folder,
            ignore_list,
            green_list,
            verbose,
            args.cmd,
            args.scp_host,
            args.force_update,
        )
    else:
        generate_json(args.folder, ignore_list, green_list, args.json, verbose)


if __name__ == "__main__":
    main()
