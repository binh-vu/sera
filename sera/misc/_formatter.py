from __future__ import annotations

import subprocess
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from sera.typing import Language
from tqdm import tqdm


@dataclass
class File:
    path: Path
    language: Language


class Formatter:
    instance = None

    def __init__(self):
        self.pending_files: list[File] = []

    @staticmethod
    def get_instance():
        if Formatter.instance is None:
            Formatter.instance = Formatter()
        return Formatter.instance

    def register(self, file: File):
        self.pending_files.append(file)

    def process(self):
        """Format pending files in parallel"""

        def format_file(file: File):
            if file.language == Language.Typescript:
                try:
                    subprocess.check_output(
                        ["npx", "prettier", "--write", str(file.path.absolute())],
                        cwd=file.path.parent,
                    )
                except subprocess.CalledProcessError as e:
                    print(f"Error formatting {file.path}: {e}")
                    raise
            else:
                raise NotImplementedError(
                    f"Formatting not implemented for {file.language}"
                )

        if len(self.pending_files) == 0:
            return

        with ThreadPoolExecutor() as executor:
            list(
                tqdm(
                    executor.map(format_file, self.pending_files),
                    total=len(self.pending_files),
                    desc="Formatting files",
                )
            )

        self.pending_files.clear()
