import argparse
import re
import sqlite3
import pathlib
import contextlib
import secrets
import hashlib
from typing import Dict, List, Optional, Union

import jinja2
import pandas as pd

from labelrepo import database, repo, displays
from labelrepo.projects.participant_demographics import _interpreter
from labelrepo.dbutils import select_annotations


def _get_labelbuddy_file(
    project_name: str, annotator_name: str
) -> pathlib.Path:
    return pathlib.Path(
        "projects",
        project_name,
        "annotations",
        f"{annotator_name}.labelbuddy",
    )


def _get_document_summaries(all_annotations: pd.DataFrame) -> List[Dict]:
    if not all_annotations.shape[0]:
        return []
    all_docs = []
    for (
        project_name,
        annotator_name,
        doc_md5,
    ), anno in all_annotations.groupby(
        ["project_name", "annotator_name", "doc_md5"]
    ):
        pmcid = anno["pmcid"].iloc[0].tolist()
        doc = {
            "project_name": project_name,
            "annotator_name": annotator_name,
            "pmcid": pmcid,
            "title": anno["title"].iloc[0],
            "annotation_stacks": _get_annotation_stacks(anno),
            "doc_uid": secrets.token_hex(4),
            "doc_md5": doc_md5,
        }
        try:
            doc["participants"] = _interpreter.DocAnnotations(anno)
            error = doc["participants"].error
            if error is not None:
                doc["extraction_failed"] = True
                doc["error_message"] = str(error)
            for g_name, _, sg in doc["participants"].subgroups():
                if g_name == "patients" and "diagnosis" not in sg.attributes:
                    doc["warnings"] = doc.get("warnings", []) + [
                        "missing diagnosis"
                    ]
                if "count" not in sg.attributes:
                    doc["warnings"] = doc.get("warnings", []) + [
                        "missing count"
                    ]
        except Exception as error:
            doc["extraction_failed"] = True
            doc["error_message"] = str(error)
            doc["participants"] = None
            doc["error"] = error
        all_docs.append(doc)
    return all_docs


def _get_doc_positions_in_db(db_path: pathlib.Path) -> Dict:
    full_db_path = repo.repo_root() / db_path
    if not full_db_path.is_file():
        return {}
    with contextlib.closing(sqlite3.connect(full_db_path)) as connection:
        with connection:
            docs = connection.execute(
                "select lower(hex(content_md5)), id from document order by id;"
            )
        return {
            row[0]: {"id": row[1], "position": i}
            for (i, row) in enumerate(docs)
        }


def _add_positions_in_db(
    doc_summaries: List[Dict], project_name: str, annotator_name: str
) -> None:
    lb_file = _get_labelbuddy_file(project_name, annotator_name)
    positions = _get_doc_positions_in_db(lb_file)
    for doc in doc_summaries:
        md5 = doc["doc_md5"]
        if md5 in positions:
            doc.update(
                {
                    "position_in_labelbuddy_file": positions[md5]["position"],
                    "labelbuddy_file": str(lb_file),
                }
            )


def select_participants_annotations():
    return select_annotations(
        labels=_interpreter.demographics_labels()
    )


def _get_jinja_env() -> jinja2.Environment:
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(
            pathlib.Path(__file__).resolve().parent / "_data" / "templates",
            encoding="UTF-8",
        ),
        autoescape=True,
    )
    env.filters["md5"] = lambda text: hashlib.md5(
        text.encode("utf-8")
    ).hexdigest()[:8]
    return env


def get_participant_demographics(include_locations=False) -> pd.DataFrame:
    all_anno = select_participants_annotations()
    all_docs = _get_document_summaries(all_anno)
    all_rows = []
    for doc in all_docs:
        if doc.get("extraction_failed", False):
            continue
        doc_info = {
            k: doc[k] for k in ("project_name", "annotator_name", "pmcid")
        }
        for gn, sgn, subgroup in doc["participants"].subgroups():
            row = {"group_name": gn, "subgroup_name": sgn}
            row.update(doc_info)
            row[f"start_char"] = []
            row[f"end_char"] = []
            for k, v in subgroup.attributes.items():
                row[k] = v.value
                if include_locations:
                    row[f"start_char"] += [v.start_char for v in v.sources]
                    row[f"end_char"] += [v.end_char for v in v.sources]
            for sex in ("female", "male"):
                try:
                    row[f"{sex} count"] = (
                        subgroup.children[sex].attributes["count"].value
                    )
                except KeyError:
                    pass
            all_rows.append(row)
    return pd.DataFrame(all_rows)


def _get_template_data(
    database_file: Optional[Union[str, pathlib.Path]] = None
) -> Dict:
    if database_file is not None:
        connection = sqlite3.connect(database_file)
    else:
        connection = database.get_database_connection()
    with contextlib.closing(connection), connection:
        label_color_rows = connection.execute(
            "select name, coalesce(color, '#00ffff') as color from label "
            "where name in ('patients', 'healthy')"
        ).fetchall()
    label_colors = {}
    for name, color in label_color_rows:
        match = re.match(r"#(..)(..)(..)", color)
        if match is not None:
            label_colors[name] = [int(p, 16) for p in match.groups()]
    return {"label_colors": label_colors}


def get_report(
    annotator_name: Optional[str] = None,
    project_name: Optional[str] = None,
    pmcid: Optional[int] = None,
    standalone: bool = False,
    errors_only: bool = False,
) -> str:
    all_anno = select_participants_annotations(
        annotator_name=annotator_name, project_name=project_name, pmcid=pmcid
    )
    all_docs = _get_document_summaries(all_anno)
    if (
        project_name is not None
        and annotator_name is not None
        and pmcid is None
    ):
        _add_positions_in_db(all_docs, project_name, annotator_name)
        key = lambda d: (
            d.get("position_in_labelbuddy_file", -1),
            d["pmcid"],
        )
    else:
        key = lambda d: (d["pmcid"], d["project_name"], d["annotator_name"])
    if errors_only:
        all_docs = [
            doc
            for doc in all_docs
            if doc.get("warnings") or doc.get("extraction_failed")
        ]
    all_docs = sorted(all_docs, key=key)
    jinja_env = _get_jinja_env()
    template = jinja_env.get_template("report.html")
    info = {
        "documents": all_docs,
        "standalone": standalone,
        "no_doc_positions": True,
    }
    if errors_only:
        info["title"] = "Participant demographics annotation errors"
    info.update(_get_template_data())
    if annotator_name is not None:
        info["annotator_name"] = annotator_name
    if project_name is not None:
        info["project_name"] = project_name
    return template.render(info)


def report_command(args: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--project_name", type=str, default=None)
    parser.add_argument("-a", "--annotator_name", type=str, default=None)
    parser.add_argument("-A", "--all_annotators", action="store_true")
    parser.add_argument(
        "-e",
        "--errors_only",
        action="store_true",
        help="only show annotations with errors or warnings.",
    )
    parsed_args = parser.parse_args(args)
    if parsed_args.all_annotators:
        annotator_name = None
    elif parsed_args.annotator_name is None:
        annotator_name = repo.annotator_name()
    else:
        annotator_name = parsed_args.annotator_name
    project_name = parsed_args.project_name
    html = get_report(
        annotator_name=annotator_name,
        project_name=project_name,
        standalone=True,
        errors_only=parsed_args.errors_only,
    )
    out_dir = repo.repo_root() / "analysis" / "data" / "reports"
    out_dir.mkdir(exist_ok=True, parents=True)
    proj_repr = "" if project_name is None else f"_{project_name}"
    annotator_repr = "" if annotator_name is None else f"_{annotator_name}"
    err_repr = "_errors" if parsed_args.errors_only else ""
    out_file = (
        out_dir
        / f"participants{err_repr}_report{annotator_repr}{proj_repr}.html"
    )
    out_file.write_text(html)
    print(f"Report saved in {out_file}")


def _get_annotation_stacks(annotations: pd.DataFrame) -> List[Dict]:
    stacks = []
    for _, anno in annotations.groupby(
        ["doc_md5", "project_name", "annotator_name", "start_char", "end_char"]
    ):
        first_anno = anno.iloc[0].to_dict()
        prefix, selected_text, suffix = displays.split_annotation_context(
            first_anno
        )
        anno_stack = {
            "start_char": first_anno["start_char"],
            "end_char": first_anno["end_char"],
            "prefix": prefix,
            "selected_text": selected_text,
            "suffix": suffix,
            "annotations": anno.to_dict(orient="records"),
        }
        stacks.append(anno_stack)
    return stacks


def get_annotation_stacks_display(
    annotations: pd.DataFrame, standalone=False
) -> str:
    stacks = _get_annotation_stacks(annotations)
    jinja_env = _get_jinja_env()
    template = jinja_env.get_template("annotation_stack_list.html")
    html = template.render(
        {"standalone": standalone, "annotation_stacks": stacks}
    )
    return html
