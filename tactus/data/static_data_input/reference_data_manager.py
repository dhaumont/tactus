"""Static data checker tool."""

import argparse
import json
import os
import sys
from pathlib import Path

from pathspec import PathSpec

# ---- Helpers

def append_file(files, file_path, filename, root_folder, verbose):
    if  os.path.exists(file_path):
        file_size = os.path.getsize(file_path)
        relative_path = os.path.relpath(file_path, root_folder)
        files.append({"filename": filename, "relative_path": relative_path, "size": file_size})
        if verbose:
            print(f"{filename}, {file_size}")
    else:
        print(f"Warning: skip {filename}: file not found in folder {root_folder}")
        
def get_files_from_dir(root_folder, verbose):
    files = []
    for root, dirs, filenames in os.walk(root_folder, followlinks=True):
        for filename in filenames:
            file_path = os.path.join(root, dirs, filename)
            append_file(files, file_path, filename, root_folder, verbose)
    return files

def get_files_from_flat_list(input_file, root_folder, verbose):
    files = []
    print("get_files_from_flat_list:")
    print(f"input_file: {input_file}")
    lines = Path(input_file).read_text().splitlines()
    print(f"lines: {lines}")
    for filename in lines:
        file_path = os.path.join(root_folder,filename)
        append_file(files, file_path, filename, root_folder, verbose)
        

    return files

def create_set(data):
    files = set()
    for file in data["files"]:
       files.add(file["filename"])
    return files
   
def write_json(data, output_json):
    
    with open(output_json, "w") as json_file:
        json.dump(data, json_file, indent=4)

    print(f"JSON file '{output_json}' generated successfully.")


def generate_json(files, output_json, root_folder):

    data = {"folder": root_folder, "files": files}
    write_json(data, output_json)
    
def get_verification_key(file_path):
    """Return the key used to check file consistency."""
    return os.path.getsize(file_path)

def report_as_git(missing_files, unknown_files, key_mismatch):
    # report_as_git results

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

# ---- Comparison functions

def check_dir(json_file, folder_path, ignore_list, verbose):
    """check_dir files listed in the JSON."""
        
    folder_files = get_files_from_dir(folder_path)
        
    with open(json_file, "r") as f:
        data = json.load(f)
    
    diff(json_file,)
    reference_folder = data["folder"]

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
    return missing_files, unknown_files, key_mismatch

def append(data,other_data,force_update):
   files_set = create_set(data)
   
   for other in other_data["files"]:
       relative_path = other["relative_path"]
          
       if not relative_path in files_set:
           data["files"].append(other)
   
def remove(data,other_data,force_update):   
   files_set = create_set(data)
   
   for other in other_data["files"]:
       relative_path = other["relative_path"]
   
       if not relative_path in files_set:
            item = next((x for x in data["files"] if x["relative_path"] == relative_path), None)
            if item:
                data["files"].remove(item)
   
def list_content(json_file):
   with open(json_file, "r") as f:
        data = json.load(f)
   reference_folder = data["folder"]

   for file in data["files"]:
        relative_path = file["relative_path"]
        file_path = os.path.join(reference_folder, relative_path)        
        print(file_path)


def boolean_op(operation, json_file, other_json_file,result_json_file,force_update):

   with open(json_file, "r") as f:
        data = json.load(f)
   
   with open(other_json_file, "r") as f:
        other_data = json.load(f)

   operation(data, other_data, force_update)
    
   write_json(data,result_json_file)

# ---- high level

def append(json_file, other_json_file, result_json_file, force_update):
    boolean_op(append,json_file, other_json_file,result_json_file, force_update)

def remove(json_file, other_json_file,result_json_file, force_update):
    boolean_op(remove,json_file, other_json_file, result_json_file, force_update)

# ---- Main folder

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="File validation script.")

    parser.add_argument(
        "--from_list", help="Path to required file of allowed files and folders.", default=None
    )
    parser.add_argument("--checkdir", help="check directory against json", default=None)    
    parser.add_argument("--append", help="other json file", default=None)
    parser.add_argument("--remove", help="other json file", default=None)
    parser.add_argument("--json", help="JSON file", default=None)
    parser.add_argument("--from_dir", help="Create a json file with the content of the directory", default=None)
    parser.add_argument("--from_list", help="Create a json file with the content of the files in the list", default=None)
    parser.add_argument("--output", help="Output JSON file", default=None)
    
    parser.add_argument("--force_update", action="store_true", help="verbose mode")
    parser.add_argument("--ignore_list", help="JSON file", default=None)

    parser.add_argument("--verbose", action="store_true", help="verbose mode")

    args = parser.parse_args()
    if not args.json:
        print("Please provide a json file name")
        sys.exit(1)

    if args.from_list:
       files = get_files_from_flat_list(args.file_list, args.folder, args.verbose)
       generate_json(files, args.json, args.folder,args.verbose)
    elif args.from_dir:
       files = get_files_from_dir(args.from_dir, args.folder, args.verbose)
       generate_json(files, args.json, args.folder,args.verbose)
    elif args.checkdir:
       missing_files, unknown_files, key_mismatch = check_dir(args.json, args.check_dir, args.ignore_list, args.verbose)
       report_as_git(missing_files, unknown_files, key_mismatch)
    elif args.append:
        append(args.json,args.append, args.output, args.force_update)
    elif args.remove:
        remove(args.json,args.append, args.output, args.force_update)    
    else:
        list_content(args.json)

if __name__ == "__main__":
    main()
