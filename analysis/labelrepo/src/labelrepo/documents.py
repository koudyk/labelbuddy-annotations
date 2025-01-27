import pathlib
import json
from collections import defaultdict
from labelrepo import repo, _utils
from labelrepo import database
import hashlib


def _load_proj_documents(keep_md5s):
    docs = defaultdict(lambda: defaultdict(dict))
    docs_paths = list(pathlib.Path('projects').glob('*/documents/*.jsonl'))
    for file in docs_paths:
        with open(file, 'r') as f:
            for line in f:
                doc_info = json.loads(line)
                doc_row, doc_info = _utils.process_doc_info(doc_info)

                if 'pmcid' in doc_info['metadata']:
                    id = f"pmcid_{doc_info['metadata']['pmcid']}"
                elif 'pmid' in doc_info['metadata']:
                    id = f"pmid_{doc_info['metadata']['pmid']}"

                if doc_row['md5'] in keep_md5s:
                    docs[id][doc_row['md5']] = doc_info

    return docs, docs_paths


def get_project_doc_md5(project_name):
    project_root_dir = repo.repo_root() / "projects" / project_name
    annotation_files = (project_root_dir / "annotations").glob("*.jsonl")

    # Load all documents that are annotated
    annotated_docs = set()
    for f in annotation_files:
        annotations = _utils.read_json(f)
        for doc_info in annotations:
            annotated_docs.add(doc_info["utf8_text_md5_checksum"])

    return annotated_docs


def _project_documents(project_name):
    project_root_dir = repo.repo_root() / "projects" / project_name

    annotation_files = (project_root_dir / "annotations").glob("*.jsonl")

    # Load all documents that are annotated
    annotated_docs = set()
    for f in annotation_files:
        annotations = _utils.read_json(f)
        for doc_info in annotations:
            annotated_docs.add(doc_info["utf8_text_md5_checksum"])
                    
    docs, docs_paths = _load_proj_documents(annotated_docs)

    # Write out documents in central location
    central_documents = repo.repo_root() / "documents"
    central_documents.mkdir(exist_ok=True)
    n_same, n_new_hash, n_new = 0, 0, 0
    for id, doc_md5s in docs.items():
        for md5, doc_info in doc_md5s.items():
            file = central_documents / f'{id}.jsonl'
            # Read file, check if doc exists
            if file.exists():
                with open(file, 'r') as f:
                    for line in f:
                        existing_doc = json.loads(line)
                        if existing_doc['text'] == doc_info['text']:
                            n_same += 1
                            break
                    else:
                        with open(file, 'a') as f:
                            f.write(json.dumps(doc_info) + '\n')
                            n_new_hash += 1
            else:
                with open(file, 'w') as f:
                    f.write(json.dumps(doc_info) + '\n')
                    n_new += 1

    return n_same, n_new_hash, n_new


def checkin_docs(project_name=None):
    """ Centralize annotated documents in the projects """
    if project_name is None:
        # Exclude "template_project"
        all_project_dirs = [
            p for p in pathlib.Path('projects').glob("*") if p.name != "template_project"
        ]
    else:
        all_project_dirs = [pathlib.Path('projects') / project_name]

    n_same, n_new_hash, n_new = 0, 0, 0
    for project_dir in all_project_dirs:
        stats = _project_documents(project_dir.name)
        n_same += stats[0]
        n_new_hash += stats[1]
        n_new += stats[2]

    print("Document centralization complete")
    print(f"{n_new} new, {n_new_hash} new hash, {n_same} documents already exist")


def _load_md5s(project_name, pmcids):
    """ Loads ids annotated in the project """
    # Get all ids for each project
    connection = database.get_database_connection()

    q = f"""SELECT project_name, pmcid, pmid, doc_md5 FROM
                                detailed_annotation
                                WHERE project_name = '{project_name}'
                                """

    if pmcids:
        q += f"AND pmcid IN ({','.join(pmcids)})"

    cur = connection.execute(q)

    # Write out pmcids for each project
    md5s = defaultdict(set)
    for row in cur.fetchall():
        if row['pmcid']:
            _id = f"pmcid_{row['pmcid']}"
        else:
            _id = f"pmid_{row['pmid']}"

        md5s[_id].add(row['doc_md5'])

    # Set to list
    md5s = {k: list(v) for k, v in md5s.items()}

    return md5s


def load_central_documents(md5s):
    """ Loads documents from the central repository """
    doc_path = repo.repo_root() / 'documents'

    # Load documents from central repository
    docs = []
    for id, ann_md5s in md5s.items():
        doc_file = doc_path / f"{id}.jsonl"
        if doc_file.exists():
            with open(doc_file, 'r') as f:
                for line in f:
                    doc = json.loads(line)
                    doc_md5 = hashlib.md5(doc["text"].encode("utf-8")).hexdigest()
                    if doc_md5 in ann_md5s:
                        docs.append(doc)

    return docs


def checkout_docs(project_name, batch_size=200, pmcids_file=None, prefix=None):
    """ Checkout documents from the central repository into the project """
    project_dir = pathlib.Path('projects') / project_name

    pmcids = None
    if pmcids_file:
        with open(pmcids_file, 'r') as f:
            pmcids = f.read().splitlines()

    all_md5s = _load_md5s(project_name, pmcids)

    docs = load_central_documents(all_md5s)

    # Write the documents to the project directory
    docs_dir = project_dir / 'documents'
    docs_dir.mkdir(exist_ok=True)

    for i in range(0, len(docs), batch_size):
        batch = docs[i:i+batch_size]
        batch_file = docs_dir / f"{prefix or 'batch'}_{i//batch_size}.jsonl"
        with open(batch_file, 'w') as f:
            for doc in batch:
                f.write(json.dumps(doc))
                f.write('\n')
