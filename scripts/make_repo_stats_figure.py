#! /usr/bin/env python3

import itertools
import pandas as pd
import plotly.graph_objects as go

from labelrepo import database, repo

connection = database.get_database_connection()

df = pd.read_sql(
    """
select project, count(distinct doc_id) as documents,
    count(distinct label_id) as labels,
    count(distinct annotator_id) as annotators,
    count(*) as annotations from
    annotation group by project order by documents desc;
""",
    connection,
)

row_colors = list(
    itertools.islice(itertools.cycle(("#f0f0f0", "#ffffff")), df.shape[0])
)
fill_color = ([row_colors * df.shape[1]],)
fig = go.Figure(
    data=[
        go.Table(
            columnwidth=[0.9, 0.5, 0.5, 0.5, 0.5],
            header=dict(
                values=[f"<b>{c.capitalize()}</b>" for c in df.columns],
                align="left",
                font=dict(size=16, color="black"),
                fill_color="#eeeeee",
                line_color="#dddddd",
            ),
            cells=dict(
                values=df.values.T,
                align="left",
                height=35,
                font=dict(size=16, color="black"),
                fill_color="white",
                line_color="#dddddd",
            ),
        )
    ]
)

fig.update_layout(width=700, height=170)
fig.update_layout(margin=dict(l=10, r=10, b=10, t=10))

fig_dir = repo.repo_root() / "analysis" / "book" / "assets" / "generated"
fig_dir.mkdir(exist_ok=True, parents=True)
fig.write_image(fig_dir / "repo_stats.svg")
