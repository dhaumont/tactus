#!/usr/bin/env python3
"""Build the green list of static data files referenced from deode logs and symlinks.

Python port of ``green_from_logs_atos_50t2.sh``.

The script collects paths under ``SOURCE_DIR`` from two sources:

1. Symlinks located under ``$SCRATCH/deode`` whose target lies within ``SOURCE_DIR``.
2. Log files (``*.1``) located under ``$HOME/deode_ecflow`` containing references
   to ``SOURCE_DIR`` through ``ln -sf``, ``ln -s``, ``cp`` or ``->`` patterns.

The resulting relative paths (with ``SOURCE_DIR/`` stripped) are written, sorted
and deduplicated, to ``cy50t2/.green``.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

SOURCE_DIR = "/ec/project/accord/tactus/"
GREEN = Path("cy50t2/.green")


def _iter_symlinks(root: Path):
    """Yield every symlink located below *root* (following directory symlinks)."""
    if not root.exists():
        return
    for dirpath, dirnames, filenames in os.walk(root, followlinks=True):
        for name in dirnames + filenames:
            path = Path(dirpath) / name
            if path.is_symlink():
                yield path


def collect_symlink_targets(scratch_deode: Path, source_dir: str) -> list[str]:
    """Return the targets of symlinks under *scratch_deode* pointing into *source_dir*."""
    targets: list[str] = []
    for link in _iter_symlinks(scratch_deode):
        try:
            target = os.readlink(link)
        except OSError:
            continue
        if source_dir in target:
            targets.append(target)
    return targets


def _iter_log_files(root: Path):
    """Yield every ``*.1`` file located below *root*."""
    if not root.exists():
        return
    yield from root.rglob("*.1")


# Regexes used to extract paths from ecflow log lines.
#
# The original shell pipelines were:
#
#   grep "| INFO" | cut -d'|' -f3 | grep "ln -sf" | cut -d' ' -f4
#   grep -v "| INFO" | grep "ln -s" | cut -d' ' -f6
#   grep " cp " | cut -d'|' -f3 | cut -d' ' -f3
#   grep "->" | cut -d'>' -f2
_RE_INFO_LN_SF = re.compile(r"\|\s*INFO[^|]*\|([^|]*)")
_RE_LN_S = re.compile(r"\bln\s+-s[a-zA-Z]*\s+(\S+)\s+(\S+)")
_RE_CP = re.compile(r"\|([^|]*\s+cp\s+[^|]*)")
_RE_ARROW = re.compile(r"->(.*)$")


def _split_fields(line: str) -> list[str]:
    """Split *line* on runs of whitespace, mimicking ``cut -d' ' -f<n>``.

    ``cut -d' '`` uses a single space as delimiter; empty fields are produced
    for repeated spaces. We reproduce that behaviour so that field numbering
    matches the shell script exactly.
    """
    return line.rstrip("\n").split(" ")


def extract_paths_from_log_line(line: str, source_dir: str) -> list[str]:
    """Extract candidate paths from a single log *line*.

    The rules mirror the four shell pipelines that scan ``*.1`` files.
    """
    if source_dir not in line:
        return []

    paths: list[str] = []
    stripped = line.rstrip("\n")

    # Rule 1: lines tagged "| INFO" containing "ln -sf" -> field 4 of the message.
    if "| INFO" in stripped and "ln -sf" in stripped:
        parts = stripped.split("|")
        if len(parts) >= 3:
            message = parts[2]
            fields = _split_fields(message)
            if len(fields) >= 4:
                paths.append(fields[3])

    # Rule 2: lines NOT tagged "| INFO" containing "ln -s" -> field 6.
    if "| INFO" not in stripped and "ln -s" in stripped:
        fields = _split_fields(stripped)
        if len(fields) >= 6:
            paths.append(fields[5])

    # Rule 3: lines containing " cp " -> third whitespace-separated field of
    # the message (part after the second "|").
    if " cp " in stripped:
        parts = stripped.split("|")
        if len(parts) >= 3:
            message = parts[2]
            fields = _split_fields(message)
            if len(fields) >= 3:
                paths.append(fields[2])

    # Rule 4: lines containing "->" -> everything after the first ">".
    if "->" in stripped:
        idx = stripped.find(">")
        if idx != -1:
            paths.append(stripped[idx + 1 :])

    return paths


def collect_paths_from_logs(logs_root: Path, source_dir: str) -> list[str]:
    """Scan every ``*.1`` file under *logs_root* and return the extracted paths."""
    collected: list[str] = []
    for log_file in _iter_log_files(logs_root):
        try:
            with open(log_file, "r", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    collected.extend(extract_paths_from_log_line(line, source_dir))
        except OSError:
            continue
    return collected


def normalise(paths: list[str], source_dir: str) -> list[str]:
    """Strip *source_dir* prefix, collapse ``//`` and drop leading spaces.

    Mirrors: ``sed -e "s|SOURCE_DIR/||g" | sed -e "s|//|/|g" | sed -e "s/^ //g"``.
    """
    prefix = f"{source_dir}/"
    cleaned: list[str] = []
    for raw in paths:
        item = raw.replace(prefix, "")
        item = item.replace("//", "/")
        if item.startswith(" "):
            item = item[1:]
        cleaned.append(item)
    return cleaned


def main() -> None:
    scratch = os.environ.get("SCRATCH")
    home = os.environ.get("HOME")

    if not scratch:
        raise RuntimeError("Environment variable SCRATCH is not set")
    if not home:
        raise RuntimeError("Environment variable HOME is not set")

    scratch_deode = Path(scratch) / "deode"
    logs_root = Path(home) / "deode_ecflow"

    collected: list[str] = []
    collected.extend(collect_symlink_targets(scratch_deode, SOURCE_DIR))
    collected.extend(collect_paths_from_logs(logs_root, SOURCE_DIR))

    # Hardcoded entry appended by the original script.
    collected.append(f"{SOURCE_DIR}/climate/GMTED2010")

    cleaned = normalise(collected, SOURCE_DIR)

    # Sort and deduplicate (equivalent to ``sort | uniq``).
    final = sorted(set(cleaned))

    GREEN.parent.mkdir(parents=True, exist_ok=True)
    with open(GREEN, "w", encoding="utf-8") as fh:
        for item in final:
            fh.write(f"{item}\n")


if __name__ == "__main__":
    main()
