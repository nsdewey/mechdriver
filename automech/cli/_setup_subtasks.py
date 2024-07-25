""" Standalone script to break an AutoMech input into subtasks for parallel execution
"""

import re
import textwrap
from pathlib import Path

import more_itertools as mit
import pandas
import pyparsing as pp
from pyparsing import common as ppc

COMMENT_REGEX = re.compile(r"#.*$", flags=re.M)

DEFAULT_GROUPS = (
    ("els", "spc"),
    ("els", "pes"),
    ("thermo", "spc"),
    ("kin", None),
)

SUBTASK_DIR = ".subtasks"


def main(
    path: str | Path,
    groups: tuple[tuple[str, str | None], ...] = DEFAULT_GROUPS,
) -> tuple[pandas.DataFrame, ...]:
    """Creates run directories for each task/species/TS and returns the paths in tables

    Task types: 'els', 'thermo', or 'kin'
    Subtask types: 'spc', 'pes', or `None` (=all species and/or reactions)

    :param path: The path to the AutoMech input to split into subtasks
    :param groups: The subtasks groups to set up, as pairs of task and subtask types
    :return: DataFrames of run paths, whose columns (species/TS index) are independent
        and can be run in parallel, but whose rows (tasks) are potentially sequential
    """
    return tuple(
        setup_subtask_group(path, t, s, group_id=i) for i, (t, s) in enumerate(groups)
    )


def setup_subtask_group(
    source_path: str | Path,
    task_type: str,
    key_type: str | None = None,
    group_id: str | int | None = None,
) -> pandas.DataFrame:
    """Set up a group of subtasks from a run dictionary, creating run directories and
    returning them in a table

    :param source_path: The path to the AutoMech input to split into subtasks
    :param task_type: The type of task: 'els', 'thermo', or 'kin'
    :param key_type: The type of subtask key: 'spc', 'pes', or `None`
    :return: A DataFrame of run paths, whose columns (subtasks) are independent and can
        be run in parallel, but whose rows (tasks) are potentially sequential
    """

    def _subtask_directory(key):
        id_str_ = "{:02d}".format
        subtask_dir = key
        if isinstance(key, tuple):
            subtask_dir = "_".join(map(id_str_, key))
        if isinstance(key, int):
            subtask_dir = id_str_(key)
        assert isinstance(subtask_dir, str), f"Invalid subtask key: {key}"
        return subtask_dir

    def _subtask_block(key):
        if isinstance(key, tuple):
            assert len(key) == 2, f"PES key does not have 2 elements: {key}"
            pes_idx, chn_idx = key
            return f"{pes_idx}: {chn_idx}"
        assert isinstance(key, int), f"Invalid subtask key: {key}"
        return f"{key}"

    # Read input files from source path
    source_path = Path(source_path)
    file_dct = read_input_files(source_path)
    run_dct = parse_run_dat(file_dct.get("run.dat"))
    run_dct["input"] = subtask_input_block_from_run_dict(run_dct)

    # Create the path for the subtask directories
    root_path = source_path / SUBTASK_DIR
    root_path.mkdir(exist_ok=True)

    # Form a prefix for the task/subtask type
    if group_id is None:
        type_keys = [task_type] + ([] if key_type is None else [key_type])
        return "_".join(type_keys)
    group_id = str(group_id)

    # Blocks that must be included in the run.dat
    block_keys = ["input"] + (["pes", "spc"] if key_type is None else [key_type])

    # Parse tasks and subtask keys for this group
    tasks = tasks_from_run_dict(run_dct, task_type, key_type)
    all_key = "all"
    keys = subtask_keys_from_run_dict(run_dct, key_type, all_key=all_key)

    # Create directories for each subtask and save the paths in a DataFrame
    row_dcts = []
    for num, (task_name, task_line) in enumerate(tasks):
        row_dct = {"task": task_name}
        task_path = root_path / f"{group_id}_{num:02d}_{task_name}"
        print(f"Setting up subtask directories in {task_path}")
        task_run_dct = {k: v for k, v in run_dct.items() if k in block_keys}
        task_run_dct[task_type] = task_line
        for key in keys:
            # Generate the subtask path
            subtask_path = task_path / _subtask_directory(key)
            subtask_path.mkdir(parents=True, exist_ok=True)
            # Generate the input file dictionary
            subtask_run_dct = task_run_dct.copy()
            if key != all_key:
                subtask_run_dct[key_type] = _subtask_block(key)
            subtask_file_dct = {**file_dct, "run.dat": form_run_dat(subtask_run_dct)}
            # Write the input files and append the path to the current dataframe row
            write_input_files(subtask_path, subtask_file_dct)
            row_dct[key] = subtask_path
        row_dcts.append(row_dct)

    df = pandas.DataFrame(row_dcts)

    csv_path = root_path / f"{group_id}.csv"
    print(f"Writing subtask group information to {csv_path}\n")
    df.to_csv(csv_path)
    return df


# Functions acting on the run directory as a whole
def read_input_files(run_dir: str | Path) -> dict[str, str]:
    inp_dir = Path(run_dir) / "inp"
    return {
        "run.dat": (inp_dir / "run.dat").read_text(),
        "theory.dat": (inp_dir / "theory.dat").read_text(),
        "models.dat": (inp_dir / "models.dat").read_text(),
        "mechanism.dat": (inp_dir / "mechanism.dat").read_text(),
        "species.csv": (inp_dir / "species.csv").read_text(),
    }


def write_input_files(run_dir: str | Path, file_dct: dict[str, str]) -> None:
    inp_dir = Path(run_dir) / "inp"
    inp_dir.mkdir(exist_ok=True)
    for name, contents in file_dct.items():
        (inp_dir / name).write_text(contents)


# Functions acting on run.dat data
def parse_run_dat(run_dat: str) -> dict[str, str]:
    """Parse a run.dat file into a dictionary of blocks

    :param run_dat: The contents of the run.dat file, as a string
    :return: The dictionary of the parsed run.dat file
    """

    def _parse_block(run_dat, keyword):
        start = pp.Keyword(keyword) + pp.LineEnd()
        end = pp.Keyword("end") + pp.Keyword(keyword)
        expr = pp.Suppress(... + start) + pp.SkipTo(end)("content")
        content = expr.parseString(run_dat).get("content")
        return format_block(content)

    return {
        "input": _parse_block(run_dat, "input"),
        "pes": _parse_block(run_dat, "pes"),
        "spc": _parse_block(run_dat, "spc"),
        "els": _parse_block(run_dat, "els"),
        "thermo": _parse_block(run_dat, "thermo"),
        "kin": _parse_block(run_dat, "kin"),
    }


def form_run_dat(run_dct: dict[str, str]) -> str:
    """Format the contents of a run.dat file from a run.dat dictionary

    :param run_dct: The dictionary of a parsed run.dat file
    :return: The run.dat file contents, as a string
    """
    keys = ["input", "spc", "pes", "els", "thermo", "kin"]
    run_dat = ""
    for key in keys:
        if key in run_dct:
            run_dat += f"{key}\n{format_block(run_dct.get(key))}\nend {key}\n\n"
    return run_dat


def subtask_input_block_from_run_dict(
    run_dct: dict[str, str], subtask_depth: int = 3
) -> str:
    """Get the input block of a run dictionary, with absolute paths for the RUN and SAVE
    directories

    :param run_dct: The dictionary of a parsed run.dat file
    :return: The input block, with absolute paths
    """

    def _extract_path(key: str) -> str:
        inp_block = run_dct.get("input")
        inp_block = without_comments(inp_block)
        word = pp.Word(pp.printables, exclude_chars="=")
        field = pp.Suppress(... + pp.Literal(f"{key}_prefix") + pp.Literal("="))
        expr = field + word("path")
        return expr.parseString(inp_block).get("path")

    def _resolve_path(path: str) -> str:
        path: Path = Path(path)
        # If the path is not absolute, go back the appropriate number of directories
        # from the subtask directory
        if not path.is_absolute():
            for _ in range(subtask_depth):
                path = ".." / path
        return str(path)

    run_prefix = _resolve_path(_extract_path("run"))
    save_prefix = _resolve_path(_extract_path("save"))

    return f"run_prefix = {run_prefix}\nsave_prefix = {save_prefix}"


def subtask_keys_from_run_dict(
    run_dct: dict[str, str], subtask_type: str | None = None, all_key: str = "all"
) -> tuple[object, ...] | None:
    """Extract species indices from a run.dat dictionary

    :param run_dct: The dictionary of a parsed run.dat file
    :return: A sequence of indices for each individual species
    """

    if subtask_type is None:
        return (all_key,)

    if subtask_type == "spc":
        spc_block = run_dct.get("spc")
        return parse_index_series(spc_block)

    if subtask_type == "pes":
        pes_block = run_dct.get("pes")

        colon = pp.Suppress(pp.Literal(":"))
        before_line_end = pp.FollowedBy(pp.LineEnd())
        entry = pp.Group(
            ppc.integer("pes") + colon + pp.SkipTo(before_line_end)("channels")
        )
        expr = pp.DelimitedList(entry, delim=pp.LineEnd())

        keys = []
        for res in expr.parseString(pes_block):
            pidx = res.get("pes")
            cidxs = parse_index_series(res.get("channels"))
            keys.extend((pidx, cidx) for cidx in cidxs)
        return tuple(mit.unique_everseen(keys))


def tasks_from_run_dict(
    run_dct: dict[str, str], task_type: str, subtask_type: str | None = None
) -> tuple[tuple[str, str], ...]:
    """Extract electronic structure tasks from  of a run.dat dictionary

    :param run_dct: The dictionary of a parsed run.dat file
    :param task_type: The type of task: 'els', 'thermo', or 'kin'
    :param subtask_type: The type of subtask: 'spc', 'pes', or `None`
    :return: A sequence of (task name, task line) pairs
    """
    block = run_dct.get(task_type)
    lines = [line.strip() for line in block.splitlines()]
    if task_type == "els":
        types = ("spc", "pes")
        assert subtask_type in types, f"Subtask type {subtask_type} not in {types}"
        start_key = "ts" if subtask_type == "pes" else "spc"
        return ((line.split()[1], line) for line in lines if line.startswith(start_key))

    return ((line.split()[0], line) for line in lines)


# Generic string formatting functions
def format_block(inp: str) -> str:
    """Format a block with nice indentation

    :param inp: A multiline string to be formatted
    :return: The formatted string
    """
    inp = re.sub(r"^\ *", "", inp, flags=re.MULTILINE)
    return textwrap.indent(inp, "    ")


def without_comments(inp: str) -> str:
    """Get a CHEMKIN string or substring with comments removed.

    :param inp: A CHEMKIN mechanism, as a file path or string
    :return: The string, without comments
    """
    return re.sub(COMMENT_REGEX, "", inp)


def parse_index_series(inp: str) -> tuple[int, ...]:
    r"""Parse a sequence of indices from a string separated by commas and newlines,
    with ranges indicated by 'x-y'

    Example:
        Input: '1,3, 5-9  \n  11,13-14\n23\n 27-29'
        Output: (1, 3, 5, 6, 7, 8, 9, 11, 13, 14, 23, 27, 28, 29)
    """
    dash = pp.Suppress(pp.Literal("-"))
    entry = ppc.integer ^ pp.Group(ppc.integer + dash + ppc.integer)
    delim = pp.LineEnd() ^ pp.Literal(",")
    expr = pp.DelimitedList(entry, delim=delim)
    idxs = []
    for res in expr.parseString(inp).as_list():
        if isinstance(res, int):
            idxs.append(res)
        else:
            start, stop = res
            idxs.extend(range(start, stop + 1))
    return tuple(mit.unique_everseen(idxs))
