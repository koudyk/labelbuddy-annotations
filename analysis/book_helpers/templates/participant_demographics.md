{% extends "project_page.md" %}

{% block main_content %}


Some analyses of this project's annotations are shown in [this page](../participant_demographics.py).

## How to annotate

```{code-cell}
:tags: [remove-input]

from labelrepo import displays
from labelrepo.projects import participant_demographics

def show_pmcid(pmcid):
    html = participant_demographics.get_report(
        project_name="participant_demographics",
        annotator_name="Jerome_Dockes",
        pmcid=pmcid,
        standalone=False,
    )
    return displays.HTMLDisplay(html)
```

Annotating demographic information about the participants is more complex than other projects in this repository, because studies typically involve several groups of participants, with diverse structures, and there is some variation in how the relevant information is reported.
To annotate a piece of information about a group of participants, we stack several annotations on top of each other.
We add annotations that identify the group of participants (eg patients vs controls), then an annotation that contains the information of interest (eg count, min age, etc.).
To be easily linked these annotations should be at the exact same positions, which is easy to acheive in **labelbuddy** by clicking several labels in sequence (or by first selecting an existing annotation and then clicking a new label to add it on top).

We consider that most articles roughly conform to the participant group structure depicted in the tree shown in {numref}`participants-tree-fig`.
The root contains all the participants, which are then divided in patients and healthy controls, each of which may contain several subgroups, and finally each subgroup can contain females and males.
Note that for many articles, some of the nodes will be empty -- eg studies involving only healthy controls, only one sex, etc.

```{figure} ../assets/annotate_participants.png
---
name: participants-tree-fig
---
The participant group structure and corresponding annotations.
```

### Annotation example with subgroups

In {numref}`participants-tree-fig` we see the general way of annotating information about participants.
We start by describing the most complex case but for most annotations the situation will be simpler.

This video (without sound) illustrates the annotation process that is described below.
The report on the left shows a continuously updated summary of the participants in the current document, it is launched with the `scripts/watch_participants.py` script as explained {ref}`here<using-participants-reports>`.


```{code-cell}
:tags: [remove-input]

html = """
<div style="padding:75% 0 0 0;position:relative;"><iframe src="https://player.vimeo.com/video/801946148?h=173137dc76&amp;badge=0&amp;autopause=0&amp;player_id=0&amp;app_id=58479" frameborder="0" allow="autoplay; fullscreen; picture-in-picture" allowfullscreen style="position:absolute;top:0;left:0;width:100%;height:100%;" title="participants-annotations-2023-02-24.mp4"></iframe></div><script src="https://player.vimeo.com/api/player.js"></script>
"""
displays.HTMLDisplay(html)
```

Here we annotate the count (20) of a specific subgroup, constituted of:

- Patients
- Within patients, the schizophrenia subgroup (this article also has an autism spectrum disorder subgroup of patients)
- Within the schizophrenia subgroup, the males.

To annotate this information, we select the information we want to annotate and then apply labels, starting from the top of the participants tree (the actual order doesn't matter, this is just a suggestion). 
We first click the "patients" label.

Then, as there are several patients subgroups in this article, we need to differentiate the schizophrenia subgroup.
We don't want to add new *labels* for subgroups, as we would end up with a very long list of labels, most of which are used in few papers (eg "schizophrenia", "siblings", "experts", etc.)
Instead, we rely on the **extra data** input field in **labelbuddy**.
While the "patients" annotation is still selected, we write int its **extra data** field (on the bottom left of **labelbuddy**).
We enter in there whatever name we want to give to the schizophrenia subgroup, which will act as a local identifier within the current paper.
This name is arbitrary and only serves to link the different annotations about that subgroup, here we unoriginally chose "schizophrenia".
Referring it to it again for other annotations will be easy because **labelbuddy** will propose it in a completion list whenever we are entering **extra data** for the "patients" label. 

Next, we click on the "males" label to create a new annotation, indicating that within the "patients" / "schizophrenia" subgroup, we are looking at the males.
Finally, we click on the "count" label to create a new annotation, indicating the type of information contained in our selected text.
If needed, we can use the **extra data** here again -- for example if the count was indicated as "twenty" (in English), we would enter in the **extra data** "20" (the value in numbers), to make it easier to use the annotation later.

So to summarize, the steps are:

- Select the group ("patients" or "healthy")
- Enter the subgroup identifier in the "extra data" field (with the help of the completion list if we have seen that subgroup before)
- Select the sex ("females" or "males")
- Select the label that indicates the type of information ("count", "age mean", etc.)
- If necessary add any complementary information in the "extra data" field (eg "20" when the selected text is "twenty").

When we annotate information about nodes that are higher in the participant group tree, we simply omit the labels that do not apply.
For example, if we are annotating the total count of participants (healthy and patients), we simply apply the label "count", without indicating a group, subgroup or sex.
As we see below, when we select the diagnosis, we only indicate the group and subgroup, as the diagnosis applies to both males and females.

Here are all the annotations for article discussed above, **PMC8883821**:

```{code-cell}
:tags: [remove-input]

show_pmcid(8883821)
```

### A simpler example

When the participant structure of an article is simpler, we can omit any of the labels as long as it does not introduce an ambiguity.
For example, if there is only one group of patients, we do not need to indicate a subgroup.
If the study contains only patients or only healthy participants, we do not need to use the `patients` or `healthy` labels.
Which label applies will be inferred from the presence of a `diagnosis`.
The {ref}`live report<using-participants-reports>` can help check that any information we leave out is being correctly inferred as we annotate.

Below is an example for the article **PMC3447931** where only the count is provided, for the patients and for the healthy controls.
Note that "diagnosis" implicitly refers to patients, so we can omit the group label here (but it would not be an error to add it).

```{code-cell}
:tags: [remove-input]

show_pmcid(3447931)
```

(using-participants-reports)=
## Participant demographics summaries

The repository contains utilities to extract summaries about the participant groups from an article's annotations and display them as shown in this page.

`scripts/participants_report.py` creates a report for all the articles exported from a given annotator and project.


`scripts/watch_participants.py` serves a live summary of the participant groups in the document we are currently annotating in **labelbuddy**.
From the root of the repository you can run it with:
```
scripts/watch_participants.py projects/participant_demographics/Your_Name.labelbuddy
```
(If you call it without specifying a file it will pick the most recently modified `.labelbuddy` file in the `projects/` directory.)

It will print the path to a file that you can open in a web browser and that can help to check annotations are correctly interpreted as you create them.
If possible, the report will be automatically opened in the default web browser.

See `scripts/participants_report.py --help` and `scripts/watch_participants.py --help` for details.


## Some more examples

Below are a few more examples of annotated documents to help annotators get started.

```{code-cell}
:tags: [remove-input]

from labelrepo import database
connection = database.get_database_connection()
example_pmcids = connection.execute("select distinct pmcid from detailed_annotation where annotator_name = 'Jerome_Dockes' and label_name = 'count' and pmcid not in (8883821, 3447931) limit 15").fetchall()
divs = []
for pmcid in example_pmcids:
    divs.append(show_pmcid(pmcid["pmcid"]).get_div())
displays.HTMLDisplay(f"<div>{''.join(divs)}</div>")    
```
{% endblock %}
