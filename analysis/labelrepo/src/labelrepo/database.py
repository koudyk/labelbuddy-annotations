import contextlib
import hashlib
import json
import os
import pathlib
import sqlite3
import tempfile
from typing import Optional, Mapping, Dict, Any

from labelrepo import repo, _utils


def _initialize_database(db_path: pathlib.Path) -> None:
    with contextlib.closing(sqlite3.connect(db_path)) as connection:
        with connection:
            connection.executescript(
                (_utils.package_data() / "initialize_db.sql").read_text("utf-8")
            )


def _fill_database(db_path: pathlib.Path):
    with contextlib.closing(sqlite3.connect(db_path)) as connection:
        connection.execute("pragma foreign_keys = on")
        for labels_file in _utils.glob_json(repo.repo_root() / "shared_labels"):
            _insert_labels(connection, labels_file)
        projects_root_dir = repo.repo_root() / "projects"
        all_project_dirs = sorted(
            p for p in projects_root_dir.glob("*") if p.name != "template_project"
        )
        _insert_all_documents(connection)
        for project_dir in all_project_dirs:
            if not project_dir.is_dir():
                continue
            _insert_project(connection, project_dir)
            _insert_project_labels(connection, project_dir)
            _insert_project_annotations(connection, project_dir)


def _insert_project(connection: sqlite3.Connection, project_dir: pathlib.Path) -> None:
    with connection:
        connection.execute("insert into project (name) values (?)", (project_dir.name,))


def _insert_all_documents(
    connection: sqlite3.Connection
) -> None:
    docs_dir = repo.repo_root() / "documents"

    if not docs_dir.is_dir():
        return
    print(f"Inserting documents from {docs_dir}")
    for docs_file in sorted(docs_dir.glob("*.jsonl")):
        _insert_documents(connection, docs_file)


def _insert_documents(connection: sqlite3.Connection, docs_file: pathlib.Path) -> None:
    with connection:
        with open(docs_file, "r", encoding="utf-8") as docs_fh:
            for doc_line in docs_fh:
                doc_info = json.loads(doc_line)
                doc_row, doc_info = _utils.process_doc_info(doc_info)
                doc_row['md5'] = bytes.fromhex(doc_row['md5'])
                connection.execute(
                    """
                    insert or ignore into document
                        (utf8_text_md5_checksum, text, pmcid, pmid,
                        publication_year, journal, title)
                    values (:md5, :text, :pmcid, :pmid,
                           :publication_year, :journal, :title)
                    """,
                    doc_row,
                )


def _insert_project_labels(
    connection: sqlite3.Connection, project_dir: pathlib.Path
) -> None:
    labels_dir = project_dir / "labels"
    if not labels_dir.is_dir():
        return
    print(f"Inserting labels from {labels_dir}")
    for labels_file in _utils.glob_json(labels_dir):
        _insert_labels(connection, labels_file, project_dir.name)


def _insert_labels(
    connection: sqlite3.Connection,
    labels_file: pathlib.Path,
    project_name: Optional[str] = None,
) -> None:
    labels = _utils.read_json(labels_file)
    with connection:
        for label_info in labels:
            connection.execute(
                "insert or ignore into label (name, color) values (?, ?)",
                (label_info["name"], label_info.get("color")),
            )
            if project_name is not None:
                label_id = connection.execute(
                    "select id from label where name = ?",
                    (label_info["name"],),
                ).fetchone()[0]
                connection.execute(
                    "insert into project_label (project_name, label_id) "
                    "values (?, ?)",
                    (project_name, label_id),
                )


def _insert_project_annotations(
    connection: sqlite3.Connection, project_dir: pathlib.Path
) -> None:
    annotations_dir = project_dir / "annotations"
    if not annotations_dir.is_dir():
        return
    print(f"Inserting annotations from {annotations_dir}")
    for annotations_file in _utils.glob_json(annotations_dir):
        _insert_annotations(connection, annotations_file)


def _insert_annotations(
    connection: sqlite3.Connection, annotations_file: pathlib.Path
) -> None:
    annotator_name = annotations_file.stem
    project = annotations_file.parents[1].name
    with connection:
        connection.execute(
            "insert or ignore into annotator (name) values (?)",
            (annotator_name,),
        )
    all_docs = _utils.read_json(annotations_file)
    all_annotations = []
    skipped_annotations = 0
    for doc_info in all_docs:
        md5 = bytes.fromhex(doc_info["utf8_text_md5_checksum"])
        doc_id = connection.execute(
            "select id from document where utf8_text_md5_checksum = ?",
            (md5,),
        ).fetchone()
        if doc_id is None:
            skipped_annotations += 1
            continue
        doc_id = doc_id[0]
        for anno_info in doc_info["annotations"]:
            label_name = anno_info["label_name"]
            with connection:
                connection.execute(
                    "insert or ignore into label (name) values (?)",
                    (label_name,),
                )
            label_id = connection.execute(
                "select id from label where name = ?", (label_name,)
            ).fetchone()[0]
            all_annotations.append(
                {
                    "annotator_name": annotator_name,
                    "label_id": label_id,
                    "start_char": anno_info["start_char"],
                    "end_char": anno_info["end_char"],
                    "extra_data": anno_info.get("extra_data", None),
                    "doc_id": doc_id,
                    "project": project,
                }
            )

    if skipped_annotations:
        print(f"Skipped {skipped_annotations} annotations in {project} due to missing documents")

    with connection:
        connection.executemany(
            """
            insert or ignore into annotation
                (doc_id, label_id, annotator_name, start_char,
                end_char, extra_data, project_name)
            values
                (:doc_id, :label_id, :annotator_name,
                :start_char, :end_char, :extra_data, :project)
            """,
            all_annotations,
        )


def make_database(
    database_path: Optional[pathlib.Path] = None, overwrite=True
) -> pathlib.Path:
    """Create a database containing all data in this repository."""
    if database_path is None:
        database_path = repo.data_dir() / "database.sqlite3"
    if database_path.is_file() and not overwrite:
        return database_path
    fd, tmp_db_path = tempfile.mkstemp(
        prefix=database_path.name, dir=database_path.parent
    )
    try:
        os.close(fd)
        tmp_db_path = pathlib.Path(tmp_db_path)
        _initialize_database(tmp_db_path)
        _fill_database(tmp_db_path)
        tmp_db_path.rename(database_path)
    finally:
        try:
            os.unlink(tmp_db_path)
        except Exception:
            pass
    print(f"Database created in {database_path}")
    return database_path


def get_database_connection(
    database_path: Optional[pathlib.Path] = None,
) -> sqlite3.Connection:
    db_path = make_database(database_path, overwrite=False).resolve()
    try:
        connection = sqlite3.connect(f"{db_path.resolve().as_uri()}?mode=ro")
    except sqlite3.OperationalError:
        connection = sqlite3.connect(db_path.resolve())
    connection.row_factory = sqlite3.Row
    return connection
