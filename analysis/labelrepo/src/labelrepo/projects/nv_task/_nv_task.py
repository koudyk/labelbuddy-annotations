from labelrepo.repo import repo_root
from labelrepo.dbutils import select_annotations
from labelrepo.documents import load_central_documents
import json

PROJ_NAME = 'nv_task'
PROJ_ROOT = repo_root() / 'projects' / 'nv_task'


def _get_labels():
    semiauto_labels = json.load(
        (PROJ_ROOT / 'labels' / 'neurovault-cobidas.json').open()
        )
    labels = [l['name'] for l in semiauto_labels]

    return labels


def _get_section(docs, pmcid, start, end):
    doc = docs[pmcid]
    for section, (s, e) in doc['metadata']['field_positions'].items():
        if start >= s and end <= e:
            return section

    return None


def load_annotations(annotator_name=None, add_sections=True):
    labels = _get_labels()
    annotations = select_annotations(
        labels=labels, project_name=PROJ_NAME, annotator_name=annotator_name
        )

    none_unsure = annotations[annotations.label_name.isin(['None', 'Unsure'])]
    annotations = annotations[~annotations.label_name.isin(['None', 'Unsure'])]
    annotations['None'] = False
    annotations['Unsure'] = False

    id_keys = ['doc_md5', 'annotator_name', 'start_char', 'end_char']
    for i, row in none_unsure.iterrows():
        matching_anns = annotations[(annotations[id_keys] == row[id_keys]).all(axis=1)]
        if len(matching_anns) > 0:
            annotations.loc[matching_anns.index, row['label_name']] = True

    if add_sections:
        unique_md5 = {}
        for pmcid, df in annotations.groupby('pmcid'):
            unique_md5[f"pmcid_{pmcid}"] = df.doc_md5.unique().tolist()

        annotated_docs = load_central_documents(unique_md5)

        # Turn into dict with key as pmcid
        annotated_docs = {
            doc['metadata']['pmcid']: doc for doc in annotated_docs
            }

        # Get section for each annotation from document metadata
        annotations['section'] = annotations.apply(
            lambda x: _get_section(annotated_docs,
                                   x.pmcid, x.start_char, x.end_char), axis=1)

    return annotations
