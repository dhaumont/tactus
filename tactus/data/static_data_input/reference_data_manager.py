"""Static data checker tool."""

import argparse
import json
import os
import sys
from pathlib import Path

from pathspec import PathSpec

def get_files_from_list(input_file, root_folder, verbose):
    files = []
    lines = Path(input_file).read_text().splitlines()
    files_list = PathSpec.from_lines("gitwildmatch", lines)
    for filename in files_list:
        file_path = os.path.join(root_folder,filename)
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            relative_path = os.path.relpath(file_path, root_folder)
            files.append({"filename": filename, "relative_path": relative_path, "size": file_size})
            if verbose:
                print(f"{filename}, {file_size}")
        else:
            print(f"Warning: {filename} not found in {root_folder}")
            
    return files
    
def generate_json(input_file, output_json, root_folder, verbose):
   
    files = get_files_from_list(input_file, root_folder, verbose)

    data = {"folder": root_folder, "files": files}

    with open(output_json, "w") as json_file:
        json.dump(data, json_file, indent=4)

    print(f"JSON file '{output_json}' generated successfully.")

def get_verification_key(file_path):
    """Return the key used to check file consistency."""
    return os.path.getsize(file_path)

def validate(json_file, folder_path, ignore_list = None, verbose = False):
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
    
            if relative_path not in expected_files:
                unknown_files.append(relative_path)
    return reference_folder, target_folder,missing_files, unknown_files, key_mismatch

def report(missing_files, unknown_files, key_mismatch):
    # Report results

    if missing_files:
        print(f"# Missing files ({len(missing_files)}):")
        for file in missing_files:         
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
        print(f"# Files with incorrect size ({len(key_mismatch)}):")
        for file, actual_key, expected_key in key_mismatch:           
            print(f"M {file} (expected: {expected_key}, found: {actual_key})")

    else:
        print("# No file with incorrect size")

def copy(missing_files, key_mismatch,from_folder, to_folder,force_update, scp_host = None):
    # Report results

    if missing_files:
        print(f"# Missing files ({len(missing_files)}):")
        for file in missing_files:         
                dir_name = os.path.dirname(f"{to_folder}/{file}")
                if scp_host:
                    print(
                        f"mkdir -p {dir_name}; scp {scp_host}:{from_folder}/{file} \
                        {to_folder}/{file}"
                    )
                else:
                    print(
                        f"mkdir -p {dir_name}; ln -s {from_folder}/{file} \
                        {to_folder}/{file}"
                    )

    if key_mismatch:
        if not force_update:
            print(
                "# Warning: files with incorrect size found, but not command \
                will be generated for them.\
                Use --force_update if you want to override them."
            )

        print(f"# Files with incorrect size ({len(key_mismatch)}):")
        for file, actual_key, expected_key in key_mismatch:
            if force_update:
                if scp_host:
                    print(
                        f"scp {scp_host}:{from_folder}/{file} \
                        {to_folder}/{file}"
                    )
                else:
                    print(f"cp {from_folder}/{file} {to_folder}/{file}")
            else:
                print(f"# Skipping - {to_folder}/{file} has inconsistent size")

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="File validation script.")
    parser.add_argument("create", action="store_true", help="convert txt to json")    
    parser.add_argument("status", action="store_true", help="check status")
    parser.add_argument("copy", action="store_true", help="check status")
    
    parser.add_argument("--folder", help="The folder to process.")
    
    parser.add_argument(
        "--file_list", help="Path to required file of allowed files and folders.", default=None
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


    if args.create:
       generate_json(args.file_list, args.json, args.folder)
    else:
        reference_folder, target_folder, missing_files, unknown_files, key_mismatch = validate(args.json, args.folder)
        if args.check:
            report(missing_files, unknown_files, key_mismatch)      
        if args.copy:
            copy(missing_files,key_mismatch,reference_folder, target_folder,args.force_update, args.scp_host)


if __name__ == "__main__":
    main()
