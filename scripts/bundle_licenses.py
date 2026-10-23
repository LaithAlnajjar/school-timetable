"""Copy installed dependency notices and inventory into an ignored distribution folder."""

import argparse
import json
import shutil
import sys
from importlib.metadata import distribution
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    target = args.output.resolve()
    target.mkdir(parents=True, exist_ok=True)
    static = Path(__file__).resolve().parents[1] / "packaging" / "licenses"
    shutil.copytree(static, target / "Qt-open-source", dirs_exist_ok=True)
    runtime = Path(__file__).resolve().parents[1] / "requirements.txt"
    packages = [
        line.split("==")[0]
        for line in runtime.read_text().splitlines()
        if "==" in line and not line.startswith("#")
    ]
    packages += ["pyinstaller", "pyinstaller-hooks-contrib"]
    inventory = []
    for name in packages:
        dist = distribution(name)
        inventory.append(
            {
                "name": dist.metadata["Name"],
                "version": dist.version,
                "license": dist.metadata.get(
                    "License-Expression", dist.metadata.get("License", "See notices")
                ),
            }
        )
        for file in dist.files or []:
            parts = file.parts
            lower = str(file).lower()
            if ".." in parts or not any(word in lower for word in ("license", "copying", "notice")):
                continue
            source = Path(dist.locate_file(file))
            if not source.is_file() or source.suffix.lower() in (".pyc", ".pyd", ".dll"):
                continue
            destination = target / name / Path(*parts)
            if not destination.resolve().is_relative_to(target):
                raise ValueError("Notice path leaves the distribution folder")
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
    for name in ("LICENSE.txt", "LICENSE"):
        source = Path(sys.base_prefix) / name
        if source.is_file():
            shutil.copyfile(source, target / "PYTHON-LICENSE.txt")
            break
    else:
        raise FileNotFoundError(
            "Python runtime license text not found; include it before distribution"
        )
    (target / "dependency-inventory.json").write_text(
        json.dumps(inventory, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
