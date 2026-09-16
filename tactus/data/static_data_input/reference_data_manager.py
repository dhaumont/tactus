"""Static data checker tool."""

import argparse
import json
import os
import sys
from pathlib import Path
from pathspec import PathSpec
import subprocess

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
    file_size = os.path.getsize(file_path) if  os.path.exists(file_path) else -1

    relative_path = os.path.relpath(file_path, root_folder)
    files.append({"filename": filename, "relative_path": relative_path, "size": file_size})
    if verbose:
        print(f"{relative_path}, {file_size}")

def get_dict_from_dir(input_folder, only, ignored, verbose):
    files = []
    ignored_rule = PathSpec.from_lines("gitwildmatch", ignored) if ignored else None
    if only:
        for filename in only:
            if ignored_rule and ignored_rule.match_file(filename):
                print(f"Warning: {filename} not added, according ignore rule")
                continue
            file_path = os.path.join(input_folder, filename)
            append_file_to_list(files, file_path, filename, input_folder, verbose)
    else:
        seen = set()

        for root, dirs, filenames in os.walk(input_folder, followlinks=True):
            relative_path = os.path.relpath(root, input_folder)
            
            if ignored_rule and ignored_rule.match_file(relative_path):
                if verbose:
                    print(f"# skip {root} according ignore rule")
                continue
            if root in seen:
                print(f"# Warning: circular dependency detected: {root} ")
                continue

            seen.add(root)

            for filename in filenames:
                if ignored_rule and ignored_rule.match_file(filename):
                    continue
                file_path = os.path.join(root, filename)
                append_file_to_list(files, file_path, filename, input_folder, verbose)

    return {"folder": input_folder, "files": files}

def get_files_from_flat_list(input_files, verbose):
    
    files = set()    
    for input_file in input_files:    
        lines = Path(input_file).read_text().splitlines()
        for filename in lines:
            files.add(filename)      
    
    
    return list(files)


def write_json(data, output_json):

    with open(output_json, "w") as json_file:
        json.dump(data, json_file, indent=4)

def get_verification_key(file_path):
    """Return the key used to check file consistency."""
    return os.path.getsize(file_path)

def report_as_git(result : ComparisonResult, long):
    # report_as_git results
        
    if len(result.common_files) > 0:
        print(f"# Common files in {result.left} and {result.right}: {len(result.common_files)}")
        if long:
            for file in result.common_files:
                print(f"{file}")
    else:
        print(f"# No common files between {result.left} and {result.right}. ")

    if len(result.missing_files) > 0:
        print(f"# Files only in {result.right}: {len(result.missing_files)}")
        if long:
            for file in result.missing_files:
                print(f"  D {file}")
    else:
        print(f"# No files only in {result.left}")

    if len(result.unknown_files) > 0:
        print(f"# Files only in {result.right}: {len(result.unknown_files)}")
        if long:
            for file in result.unknown_files:
                print(f"  ? {file}")
    else:
        print(f"# No files only in {result.right}")

    if len(result.different_files) > 0:
        print(f"# Files with incorrect size: {len(result.different_files)}")
        if long:
            for file, actual_key, expected_key in result.different_files:
                print(f"  M {file} (expected: {expected_key}, found: {actual_key})")

    else:
        print("# No file with incorrect size")
    
    if not long:
        print("Hint: use --long to get more detail")
    
def generate_copy_commands(result : ComparisonResult,command, input_folder, output_folder):
        
        for file in result.missing_files:
            print(f"{command}{input_folder}/{file} {output_folder}/{file}")
        
        for file in result.different_files:
            print(f"{command}{input_folder}/{file} {output_folder}/{file}")
            
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


def create_index_dictionary(folder, only_list, ignored_list, verbose):
    """compare_json_to_dir files listed in the JSON."""

    only = get_files_from_flat_list(only_list, verbose) if only_list else None
    ignored = get_files_from_flat_list(ignored_list, verbose) if ignored_list else None
    data = get_dict_from_dir(folder, only, ignored, verbose)

    return data

def build_file_index(output_json, folder, only_list, ignored_list, verbose):
    """compare_json_to_dir files listed in the JSON."""

    data = create_index_dictionary(folder, only_list, ignored_list, verbose)
    write_json(data,output_json)


def compare_json_to_dir(json_file, dir, only_list, ignored_list, verbose):
    """compare_json_to_dir files listed in the JSON."""

    with open(json_file, "r") as f:
        data = json.load(f)

    folder = dir if dir else data["folder"]
    other_data = create_index_dictionary(folder,only_list, ignored_list,verbose)
    
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

def build_reference(json_file, root_folder, only_list, ignored_list, verbose):

    only = get_files_from_flat_list(only_list, verbose) if only_list else None

    ignored = get_files_from_flat_list(ignored_list, verbose) if ignored_list else None

    data = get_dict_from_dir(root_folder, only, ignored, verbose)
    write_json(data, json_file)
    print(f"JSON file '{json_file}' generated successfully.")
    
def append(data,other_data,force_update):

   reverse = reverse_dict(data["files"])
   for other in other_data["files"]:
       relative_path = other["relative_path"]

       if not relative_path in reverse:
           data["files"].append(other)
           reverse[relative_path] = other

def remove(data,other_data,force_update):
   new_files = []
   other_reverse = reverse_dict(other_data["files"])
   for item in data["files"]:
       relative_path = item["relative_path"]
       if relative_path not in other_reverse:
           new_files.append(item)
   data["files"] = new_files

def list_content(json_file,verbose):
   with open(json_file, "r") as f:
        data = json.load(f)
   reference_folder = data["folder"]

   for file in data["files"]:
        relative_path = file["relative_path"]        
        file_path = os.path.join(reference_folder, relative_path)
        if verbose:
            size = file["size"]
            print(f"{reference_folder}/{file_path} {size}")
        else:
            print(f"{reference_folder}/{file_path}")

def files_list_from_logs(log_folder, output_file, root_folder):
    bash_file = "files_list_from_log_folder.sh"
    subprocess.call([bash_file,log_folder,output_file,root_folder])


# ---- Main folder

def check_parse_arguments(args):
    errors = []
    if args.action == 'diff':
         if len(args.platforms) < 2:
            errors.append(f"diff require two platforms")    
    return errors


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="File validation script.")

    parser.add_argument("action", choices=['status','build_ref','copy','show', 'diff', 'read_logs'])
    parser.add_argument("platforms", choices=['atos','lumi','leonardo'], nargs="+")
    
    parser.add_argument("--force_update", action="store_true", help="verbose mode")
    parser.add_argument("--ignore", help="list of ignore files", default=None)
    parser.add_argument("--only", help="list of green files", default=None)
    parser.add_argument("--long", action="store_true", help="long mode")
    parser.add_argument("--verbose", action="store_true", help="verbose mode")

    args = parser.parse_args()

    errors = check_parse_arguments(args)
    if len(errors) > 0:
        print("Error(s) detected:")
        for error in errors:
            print(f"  {error}")
        sys.exit(1)

    platform = args.platforms[0]
    config_files = {}
    with open("./data/config.json", "r") as f:
        config_files = json.load(f)
    root_folder = config_files[platform]["root_folder"]
    reference_json = config_files[platform]["reference_json"]
    ignore = config_files[platform]["ignore"]
    current_index_json = config_files[platform]["current_index_json"]
    
    if len(args.platforms) > 1:
        to_platform = args.platforms[1]
        to_root_folder = config_files[to_platform]["root_folder"]
        to_current_index_json  = config_files[to_platform]["current_index_json"]
        to_reference_json  = config_files[to_platform]["reference_json"]
    if args.action == 'build_ref':
        if not os.path.exists(root_folder):            
            print(f"Error - {root_folder} not found")
            exit(1)
        input_files = config_files[platform]["input"]        
        build_reference(reference_json, root_folder, input_files, ignore, args.verbose)
    elif args.action == 'status':
        print(f"Comparing {reference_json} and {root_folder}")
        if os.path.exists(root_folder):            
            print(f"Rebuilding index for {root_folder}...")
            build_file_index(current_index_json,root_folder,None, ignore, args.verbose)
        else:
            print(f"WARNING - Index could not be rebuild, {root_folder} not found")
            print(f"          Using previous index which might be outdated")
        result = compare_json_to_json(reference_json, current_index_json, args.verbose)
        result.right = root_folder
        report_as_git(result, args.long)
    elif args.action == 'diff':
        result = compare_json_to_json(reference_json,to_reference_json, args.verbose)
        report_as_git(result, args.long)
    elif args.action == 'copy':
        result = compare_json_to_json(to_reference_json,to_current_index_json, args.verbose)        
        command = "cp "
        generate_copy_commands(result,command,root_folder,to_root_folder)
    elif args.action == 'show':
        list_content(reference_json,args.verbose, args.long)
    elif args.action == 'read_logs':        
        log_folder = config_files[platform]["log_folder"]
        output_file = config_files[platform]["output_file_from_log"]        
        
        files_list_from_logs(log_folder, output_file, root_folder)
if __name__ == "__main__":
    main()
