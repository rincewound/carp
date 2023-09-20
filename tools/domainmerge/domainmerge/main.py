import sys
import json
import os

def process(directory, domain):
    # Do something with the directory
    print(f"Processing directory: {directory}")
    file_path = f"{directory}/carp.domain"
    if os.path.exists(file_path) and os.path.isfile(file_path):
        with open(f"{directory}/carp.domain", "r") as file:
            new_domain = json.load(file)
            domain[new_domain["domain"]] = new_domain


def run():
    if len(sys.argv) < 3:
        print("Please provide the start directory as a command-line argument.")
        sys.exit(1)
    start_directory = sys.argv[1]
    output_file = sys.argv[2]
    domain = {}
    for root, dirs, files in os.walk(start_directory):
        process(root, domain)
        for directory in dirs:
            process(os.path.join(root, directory), domain)
    
    with open(output_file, "w") as file:        
        json.dump(domain, file, indent=4)