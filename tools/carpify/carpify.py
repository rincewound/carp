import os
import sys
import json
import re
import subprocess

def has_pending_changes(file_path):
    try:
        git_status_cmd = ["git", "status", "--porcelain", "--untracked-files=all", file_path]
        output = subprocess.check_output(git_status_cmd).decode("utf-8").strip()
        return bool(output)
    except subprocess.CalledProcessError:
        return True         # assume pending changes if git failed

def process_single_file(file, domain):
    print(f"Processing file: {file}")
    file_lines = []
    with open(file, "r") as file_read:
        for line in file_read:      
            if line.lstrip().startswith("CARP_LOG"):
                leading_spaces = len(line) - len(line.lstrip())
                regex = r'^(.*?)\("(.*?)"\s*,\s*(.*?)\);$'
                match = re.match(regex, line)

                if match:
                    function_name = match.group(1)
                    log_message = match.group(2)
                    value = match.group(3)
                    string_id = len(domain["messages"])
                    dfmt_string = f'''CARP_DFMT("{log_message}", {domain['domain']}, {string_id}, {value}) \n'''
                    domain["messages"].append(log_message)
                    file_lines.append(f"{' ' * leading_spaces}{dfmt_string}")
                else:
                    file_lines.append(line)
                    continue      
            else:
                file_lines.append(line)            
    with open(file, "w") as file_write:
        for line in file_lines:
            file_write.write(line)

def process(directory, domain):
    current_domain = domain
    persist_domain = False
    # Do something with the directory
    print(f"Processing directory: {directory}")
    file_path = f"{directory}/carp.domain"
    if os.path.exists(file_path) and os.path.isfile(file_path):
        with open(f"{directory}/carp.domain", "r") as file:
            current_domain = json.load(file)
            persist_domain = True


    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".cpp"):
                file_path = os.path.join(root, file)
                if has_pending_changes(file_path):
                    process_single_file(file, current_domain)

    if persist_domain:
        with open(f"{directory}/carp.domain", "w") as file:        
            json.dump(current_domain, file, indent=4)
    else:
        pass


def traverse_directories(start_directory):
    domain = {"domain" : 0, "name": "unnamed domain", "messages": []}
    
    for root, dirs, files in os.walk(start_directory):
        process(root, domain)
        for directory in dirs:
            process(os.path.join(root, directory), domain)

if __name__ == "__main__":
    # Get the start directory from command-line argument
    if len(sys.argv) < 2:
        print("Please provide the start directory as a command-line argument.")
        sys.exit(1)
    start_directory = sys.argv[1]
    
    traverse_directories(start_directory)