from typing import Optional, Tuple
import contextlib
import pandas as pd
from labelrepo import database


def select_annotations(
    labels: Optional[Tuple[str]],
    annotator_name: Optional[str] = None,
    project_name: Optional[str] = None,
    pmcid: Optional[int] = None,
) -> pd.DataFrame:
    
    labels = ",".join([f"'{label}'" for label in labels])
    annotator_query = (
        "" if annotator_name is None else "and annotator_name = :annotator"
    )
    project_query = (
        "" if project_name is None else "and project_name = :project"
    )
    pmcid_query = "" if pmcid is None else "and pmcid = :pmcid"
    query = f"""
select pmcid, title, doc_md5, label_name, extra_data, selected_text,
    start_char, end_char, project_name, annotator_name,
    coalesce(label_color, '#E0E0E0') as label_color, context,
    context_start_char, context_end_char, doc_length
from detailed_annotation where label_name in ({labels})
{annotator_query}
{project_query}
{pmcid_query}
    """

    with contextlib.closing(database.get_database_connection()) as connection:
        with connection:
            all_anno = pd.DataFrame(
                map(
                    dict,
                    connection.execute(
                        query,
                        {
                            "annotator": annotator_name,
                            "project": project_name,
                            "pmcid": pmcid,
                        },
                    ).fetchall(),
                )
            )
    if not all_anno.shape[0]:
        all_anno = pd.DataFrame(
            columns="pmcid title doc_md5 label_name extra_data "
            "selected_text start_char end_char project_name "
            "annotator_name".split()
        )
    return all_anno
