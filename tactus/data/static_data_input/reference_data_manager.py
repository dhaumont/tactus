"""Static data checker tool."""

import argparse
import json
import os
import sys
from pathlib import Path

# ---- Helpers

def append_file_to_list(files, file_path, filename, root_folder, verbose):
    if  os.path.exists(file_path):
        file_size = os.path.getsize(file_path)
        relative_path = os.path.relpath(file_path, root_folder)
        files.append({"filename": filename, "relative_path": relative_path, "size": file_size})
        if verbose:
            print(f"{filename}, {file_size}")
    else:
        print(f"Warning: skip {filename}: file not found in folder {root_folder}")
        
def get_dict_from_dir(input_folder, verbose):
    files = []
    for root, dirs, filenames in os.walk(input_folder, followlinks=True):
        for filename in filenames:
            file_path = os.path.join(root, filename)
            append_file_to_list(files, file_path, filename, input_folder, verbose)
    
    return {"folder": input_folder, "files": files}    

def get_dict_from_flat_list(input_file, root_folder, verbose):
    files = []
    print("get_files_from_flat_list:")
    print(f"input_file: {input_file}")
    lines = Path(input_file).read_text().splitlines()
    print(f"lines: {lines}")
    for filename in lines:
        file_path = os.path.join(root_folder,filename)
        append_file_to_list(files, file_path, filename, root_folder, verbose)
        
    return {"folder": root_folder, "files": files}    
   
   
def write_json(data, output_json):
    
    with open(output_json, "w") as json_file:
        json.dump(data, json_file, indent=4)

    print(f"JSON file '{output_json}' generated successfully.")
    
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

def compare(item, other_data, not_found_files,mistmatch_files = None):    
    relative_path = item["relative_path"]    
    other = next((x for x in other_data["files"] if x["relative_path"] == relative_path), None)
    
    if other == None:
        not_found_files.append(relative_path)
    elif mistmatch_files != None:
        # Check if the file hash matches                    
        actual_key = item["size"]
        other_key  = other["size"]
        if actual_key != other_key:
            mistmatch_files.append((relative_path, other_key, actual_key))
    
def diff(data, other_data,verbose):

    missing_files = []
    unknown_files = []
    key_mismatch = []

    # Check if files in JSON are present on disk
    for item in data["files"]:
        compare(item,other_data,missing_files,key_mismatch)
        
    for other_item in other_data["files"]:
        compare(other_item,data,unknown_files)
        
    return missing_files, unknown_files, key_mismatch

def check_dir(json_file, dir, ignore_list, verbose):
    """check_dir files listed in the JSON."""
        
    with open(json_file, "r") as f:
        data = json.load(f)

    if dir is None:
        folder = dir if dir else data["folder"]
        
    other_data = get_dict_from_dir(folder, verbose)        
    
    missing_files, unknow_files, key_mistmatch = diff(data,other_data,verbose)
    return missing_files, unknow_files, key_mistmatch

def diff_json(json_file, other_json_file, verbose):
    with open(json_file, "r") as f:
        data = json.load(f)
        
    with open(other_json_file, "r") as f:
        other_data = json.load(f)

    return diff(data,other_data,verbose)

def append_op(data,other_data,force_update):
   
   for other in other_data["files"]:
       relative_path = other["relative_path"]
       item = next((x for x in data["files"] if x["relative_path"] == relative_path), None)
       if not item:
           data["files"].append(other)
   
def remove_op(data,other_data,force_update):      
   
   for other in other_data["files"]:
       relative_path = other["relative_path"]
   
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
    boolean_op(append_op,json_file, other_json_file,result_json_file, force_update)

def remove(json_file, other_json_file,result_json_file, force_update):
    boolean_op(remove_op,json_file, other_json_file, result_json_file, force_update)

# ---- Main folder

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="File validation script.")

    
    parser.add_argument("action", choices=['diff','show','add','rm','create'], default = 'list')
    parser.add_argument("json", help="JSON file", default='reference.json')            
    parser.add_argument("--root", help="Root folder", default = None)
    
    parser.add_argument("--force_update", action="store_true", help="verbose mode")
    parser.add_argument("--ignore", help="list of ignore files", default=None)
    parser.add_argument("--allow", help="list of green files", default=None)
    parser.add_argument("--other", help="compare with other", default=None)
    parser.add_argument("--verbose", action="store_true", help="verbose mode")

    args = parser.parse_args()
    if not args.json:
        print("Please provide a json file name")
        sys.exit(1)
    
    for path in [args.root, args.allow, args.ignore, args.other]:
        if path and not os.path.exists(path):
            print(f"ERROR {path} not found")
            sys.exit(1)
    
    if args.action == 'create':
        if not args.root:
            print("Error: please provide a root folder")            
            sys.exit(1)
        
        if args.allow:
            data = get_dict_from_flat_list(args.allow, args.root, args.verbose)
        else:    
            data = get_dict_from_dir(args.root, args.verbose)

        if args.ignore:
            ignored_data = get_dict_from_flat_list(args.ignore, args.root, args.verbose)
            remove_op(data, ignored_data, args.force_update)            
        
        write_json(data, args.json)
    
    elif args.action == 'diff':
        if not args.other:
            print("Error: --other argument missing (it can be a directory or a json file)")
            sys.exit(1)
            
        if os.path.isdir(args.other):
            missing_files, unknown_files, key_mismatch = check_dir(args.json, args.other, args.ignore_list, args.verbose)            
        else:
           missing_files, unknown_files, key_mismatch = diff_json(args.json, args.other, args.verbose)                     
        
        report_as_git(missing_files, unknown_files, key_mismatch)
    elif args.action in ['add','rm']:
        if not args.other:
            print("Error: --other argument missing (json file)")
            sys.exit(1)                
        if os.path.isdir(args.other):
            print(f"Error: {args.other} is a directotry")
            sys.exit(1)
        if args.action == "add":
            append(args.json,args.other, args.json, args.force_update)
        else:    
            remove(args.json,args.other, args.json, args.force_update)    
    elif args.action == 'show':
        list_content(args.json)

if __name__ == "__main__":
    main()
