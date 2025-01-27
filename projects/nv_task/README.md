# `Semi-automated fMRI Meta-Analysis features`

`Annotation of the tasks, conditions and contrasts used in an fMRI study, that would be useful to extract to help users perform a semi-automated meta-analysis in Neurosynth Compose`

## Papers

### How the papers were obtained
Overlap between papers in `participant_demographics` sample and NeuroVault sample.
Note that some papers were pulled with Tables, whereas some were not.

## Annotations

The goal is to annotate task-related features useful for Meta-Analysis using the NeuroVault terminology.

General 
- `Modality`: imaging modality. For simplicity, this categorical variable is split onto into several labels for each level (fMRI-BOLD, StructuralMRI, etc...)
- `TaskName`: explicit mention of a task name (e.g. Stroop). 
- `TaskDescription`: a description of the task. Especially useful when no explicit name given
- `Condition`: a condition name (e.g. "Congruent")  of the task (e.g. not between subjects experimental condition)
- `ContrastDefinition`: a contrast specification (e.g. "Congruent>Incongruent"). 

See below for more instructions on `ContrastDefinition`.

### General purpose labels
- `Unsure`: Use this label in combination with any other label to indicate task name is insure. 
- `None`: If the task name is not mentioned, use this label on the closest term that resembles a task name in the Methods section by combining with `TaskName` label.

### Type of study
- `Exclude-Meta-analysis`: If the study is a meta-analysis, use this label on the first clue that the study is a meta-analysis.
- `DesignType-RestingState`: If the study is a  resting-state study, use this label on the first clue that the study is a resting-state study.
- `Exclude-Review`: If the study is a review paper, use this label on the first clue that the study is a review paper.


### Instructions for annotators

#### Abstract
The Abstract section is of lower interest, but if a clear `TaskName` or `Modality` is found, that may be annotated.

#### Body
Otherwise, for all other keys in the Body, annotate the best example of a given key. 
For `Condition` and `ContrastDefinition`, the keys may appear multiple times. Highlight the best possible example if available.

#### Tables
Tables are often where `ContrastDefinition` are most clearly defined. 
Thus, if `Tables` are available, annotate each separate group of coordinates with a `ContrastDefinition` label for the header.
Annotate Tables independently from the body. 

If a table grouping lacks the full `ContrastDefinition` information, highlight the relevant info in Caption if available. 
For example, if G1 > G2 and G2 > G1 are both in the same table for A > B contrast, but contrast info A > B is only listed in Caption. 
Goal is to identify each group of coordinates, and the relevant information in tables to identify the corresponding `ContrastDefinition`.