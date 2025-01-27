import itertools
import json
import pathlib
from typing import List, Union, Any, Tuple
import hashlib
from typing import Mapping, Dict


def package_root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parent


def package_data() -> pathlib.Path:
    return package_root() / "_data"


def read_json(json_file: Union[str, pathlib.Path]) -> Any:
    json_file = pathlib.Path(json_file)
    if json_file.suffix == ".json":
        return json.loads(json_file.read_text("UTF-8"))
    elif json_file.suffix == ".jsonl":
        with open(json_file, "r", encoding="UTF-8") as stream:
            return [json.loads(line) for line in stream]
    raise ValueError("File extension must be .json or .jsonl")


def glob_json(directory: pathlib.Path) -> List[pathlib.Path]:
    return sorted(
        itertools.chain(directory.glob("*.json"), directory.glob("*.jsonl"))
    )


def _extract_metadata_from_text(doc_info: Mapping[str, Any]) -> Dict[str, str]:
    metadata = {}
    for field, (start, end) in doc_info["metadata"].get("field_positions", {}).items():
        metadata[field] = doc_info["text"][start:end]
    return metadata


def process_doc_info(doc_info: dict) -> Tuple[Dict[str, Any], dict]:
    metadata_field_types = {
        "pmid": int,
        "pmcid": int,
        "journal": str,
        "publication_year": int,
        "title": str,
    }

    if isinstance(doc_info["metadata"], str):
        doc_info["metadata"] = json.loads(doc_info["metadata"])
        
    doc_row = {}
    doc_row["md5"] = hashlib.md5(doc_info["text"].encode("utf-8")).hexdigest()
    doc_row["text"] = doc_info["text"]
    text_metadata = _extract_metadata_from_text(doc_info)
    for field, field_type in metadata_field_types.items():
        raw_value = doc_info["metadata"].get(
            field, text_metadata.get(field, None)
        )
        if raw_value is not None:
            try:
                doc_row[field] = field_type(raw_value)
            except (KeyError, ValueError, TypeError):
                doc_row[field] = None
        else:
            doc_row[field] = None

    return doc_row, doc_info
    