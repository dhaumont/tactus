"""Static data checker tool."""

import argparse
import json
import os
import sys
from pathlib import Path

# ---- Helpers
class ComparisonResult:
     def __init__(self):
        self.left = None
        self.right = None
        self.common_files = []
        self.missing_files = []
        self.unknown_files = []
        self.different_files = []
        
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

def report_as_git(result : ComparisonResult):
    # report_as_git results

    if len(result.common_files) > 0:
        print(f"# Common files in {result.left} and {result.right}: {len(result.common_files)}")
    else:
        print(f"# No common files between {result.left} and {result.right}. ")

    if len(result.missing_files) > 0:
        print(f"# Missing files in {result.left} ({len(result.missing_files)}):")
        for file in result.missing_files:
                print(f"  D {file}")
    else:
        print(f"# No missing files in {result.left}")

    if len(result.unknown_files) > 0:
        print(f"# Unknown files in {result.right} ({len(result.unknown_files)}):")
        for file in result.unknown_files:
            print(f"  ? {file}")
    else:
        print(f"# No unknown files in {result.right}")

    if len(result.different_files) > 0:
        print(f"# Files with incorrect size ({len(result.different_files)}):")
        for file, actual_key, expected_key in result.different_files:
            print(f"  M {file} (expected: {expected_key}, found: {actual_key})")

    else:
        print("# No file with incorrect size")

# ---- Comparison functions
def reverse_dict(data):
    reverse = {}
    for item in data:
        relative_path = item["relative_path"]
        reverse[relative_path] = item
    return reverse    

def compare(item, reverse, not_found_files,mistmatch_files = None, common_files = None):        
    relative_path = item["relative_path"]
    
    if not relative_path in reverse:
        not_found_files.append(relative_path)
    elif mistmatch_files != None or common_files != None:
        # Check if the file hash matches                    
        actual_key = item["size"]
        other_key  = reverse[relative_path]["size"]
        if actual_key != other_key:
            mistmatch_files.append((relative_path, other_key, actual_key))
        elif common_files != None:
            common_files.append(relative_path)
    
def diff(data, other_data,verbose):

    result = ComparisonResult()
    
    reverse = reverse_dict(data["files"])
    reverse_other = reverse_dict(other_data["files"])
    # Check if files in JSON are present on disk
    for item in data["files"]:
        compare(item,reverse_other, result.missing_files,result.different_files,result.common_files)
        
    for other_item in other_data["files"]:
        compare(other_item,reverse,result.unknown_files)
        
    return result

def compare_json_to_dir(json_file, dir, ignore_list, verbose):
    """compare_json_to_dir files listed in the JSON."""
        
    with open(json_file, "r") as f:
        data = json.load(f)
    
    folder = dir if dir else data["folder"]        
    other_data = get_dict_from_dir(folder, verbose)        
    
    result = diff(data,other_data,verbose)
    result.left = json_file
    result.right = folder
    return result

def compare_json_to_json(json_file, other_json_file, verbose):
    with open(json_file, "r") as f:
        data = json.load(f)
        
    with open(other_json_file, "r") as f:
        other_data = json.load(f)

    result = diff(data,other_data,verbose)
    result.left = json_file
    result.right = other_json_file
    return result

def append_op(data,other_data,force_update):
   
   reverse = reverse_dict(data["files"])
   for other in other_data["files"]:
       relative_path = other["relative_path"]

       if not relative_path in reverse:
           data["files"].append(other)
           reverse[relative_path] = other
   
def remove_op(data,other_data,force_update):      
   new_files = []
   other_reverse = reverse_dict(other_data["files"])
   for item in data["files"]:
       relative_path = item["relative_path"]   
       if relative_path not in other_reverse:
           new_files.append(item)
   data["files"] = new_files
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

def check_parse_arguments(args):
    errors = []
    if not args.input:
        errors.append("json missing")
    
    if args.action in ['create','add','rm','diff']:
        if len(args.input) < 2:
            errors.append('Not enough parameters provided')
            return errors
            
    parameter_list = args.input.copy()
    parameter_list.extend([args.allow, args.ignore])    
    for path in parameter_list:
        if path and not os.path.exists(path):
            errors.append(f'\"{path}\" not found')
                
    if args.action == 'create':
        if not os.path.isdir(args.input[1]):
            errors.append(f"{args.input[1]} is not a directory")
            
    elif args.action in ['add','rm','diff']:
        if os.path.isdir(args.input[1]):
            errors.append(f"{args.input[1]} is a directory")
            
    elif args.action == 'status':        
        if len(args.input) > 1:
            directory = args.input[1]
            if not os.path.isdir(directory):
                errors.append(f"{directory} is not a directory")
    return errors

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="File validation script.")

    
    parser.add_argument("action", choices=['diff','show','add','rm','create', 'status'], default = 'list')
    #parser.add_argument("json", help="JSON file", default='reference.json')            
    parser.add_argument("input", help="Command parameter", nargs='+')
    
    parser.add_argument("--force_update", action="store_true", help="verbose mode")
    parser.add_argument("--ignore", help="list of ignore files", default=None)
    parser.add_argument("--allow", help="list of green files", default=None)
    
    parser.add_argument("--verbose", action="store_true", help="verbose mode")

    args = parser.parse_args()
    print(args.input)
    errors = check_parse_arguments(args)
    if len(errors) > 0:
        print("Error(s) detected:")
        for error in errors:
            print(f"  {error}")
        sys.exit(1)
    
    if args.action == 'create':        
        if args.allow:
            data = get_dict_from_flat_list(args.allow, args.parameter, args.verbose)
        else:    
            data = get_dict_from_dir(args.parameter, args.verbose)

        if args.ignore:
            ignored_data = get_dict_from_flat_list(args.ignore, args.parameter, args.verbose)
            remove_op(data, ignored_data, args.force_update)            
        
        write_json(data, args.input)
    
    elif args.action == 'status':         
        directory = None if len(args.input) <= 1 else args.input[1]
        result = compare_json_to_dir(args.input[0], directory, args.ignore, args.verbose)            
        report_as_git(result)
    elif args.action == 'diff':        
        result = compare_json_to_json(args.input[0],args.input[1], args.verbose)        
        report_as_git(result)
    elif args.action in ['add','rm']:        
        if args.action == "add":
            append(args.input[0],args.input[1], args.input[0], args.force_update)
        else:    
            remove(args.input[0],args.input[1], args.input[0], args.force_update)    
    elif args.action == 'show':
        list_content(args.input)

if __name__ == "__main__":
    main()
