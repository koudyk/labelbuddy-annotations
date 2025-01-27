
#! /usr/bin/env python3

# This script is used to make a temporary copy the documents from the central repository to the projects directory using the ids.json file

import argparse
from labelrepo.documents import checkout_docs

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Copy documents for a project from the central repository."
    )
    parser.add_argument("project_name")
    parser.add_argument("--batch_size", type=int, default=200)
    parser.add_argument("--pmcids_file", type=str, default=None)
    parser.add_argument("--prefix", type=str, default=None)
    args = parser.parse_args()

    checkout_docs(args.project_name, args.batch_size, args.pmcids_file, args.prefix)
