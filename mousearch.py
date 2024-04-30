import pathlib
import re
from datetime import datetime
from itertools import islice
from math import ceil
from time import sleep
import pathlib
from tqdm import tqdm
import sys
import os
import subprocess

from common import ErrorDialog, InfoDialog, WarningDialog
from mouser_api import MouserAPI
from farnell_api import FarnellAPI

MOUSER_BIT = 1 << 1
FARNELL_BIT = 1 << 0


class Mousearch:
    def __init__(self, bom: pathlib.Path, mouser_key: str, farnell_key: str):
        self.bom = bom
        self.mouser_key = mouser_key
        self.farnell_key = farnell_key

    def generate_bom(self, top_level_schematic: pathlib.Path):
        commands = [
                "kicad-cli",
                "sch",
                "export",
                "bom",
                "--output",
                "bom.csv",
                "--fields",
                "'MPN,${QUANTITY}'",
                "--exclude-dnp",
                "--group-by",
                "MPN",
                str(top_level_schematic),
            ]
        print(commands)
        subprocess.check_output(commands)

    def run(self):
        bom = {}
        for footprint in self.board.GetFootprints():
            items_to_skip = [r"kibuzzard.*", r"LAYOUT.*", r"TP.*", r"H.*"]
            reference = footprint.GetReference()
            if any(re.search(x, reference) for x in items_to_skip):
                continue
            if not footprint.HasFieldByName("MPN"):
                ErrorDialog(
                    message=f"{footprint.GetReference()} does not have an MPN specified",
                    title="No MPN specified",
                )
                return
            else:
                mpn = footprint.GetFieldText("MPN")
                if mpn in bom:
                    bom[mpn] += 1
                else:
                    bom[mpn] = 1

        # Now have a dict with MPN: quantity
        mouser_api = MouserAPI(self.mouser_key)
        farnell_api = FarnellAPI(self.farnell_key)

        # Have to batch in 30 items per minute to avoid Mouser maximum calls per minute limit
        # WarningDialog(
        #     message=f"To avoid Mouser DDOS, this has to be rate limited to 30 items per minute. Expected completion is {ceil(len(bom) / 30)} minutes and will cause Kicad to freeze until complete.",
        #     title="This may take a while...",
        # )
        issues = {}

        found_parts = {}

        for mpn, quantity in tqdm(list(bom.items())):
            start_time = datetime.now()
            score = 0
            # Check Mouser
            if mouser_api.check_for_stock(mpn) >= quantity:
                score += MOUSER_BIT

            # Check Farnell
            if farnell_api.check_for_stock(mpn) >= quantity:
                score += FARNELL_BIT

            found_parts[mpn] = score
            while (datetime.now() - start_time).seconds < 2:
                sleep(0.1)

        # Print report in sorted order
        with open(pathlib.Path(__file__).parent.resolve() / "results.md", "w") as file:
            file.write("| MPN | Mouser | Farnell |\r")
            file.write("| --- | --- | --- |\r")
            for mpn, score in sorted(
                found_parts.items(), key=lambda item: (item[1], item[0])
            ):

                file.write(f"| {mpn} ")
                if score & MOUSER_BIT:
                    file.write("| ✅ ")
                else:
                    file.write("| ❌ ")

                if score & FARNELL_BIT:
                    file.write("| ✅ ")
                else:
                    file.write("| ❌ ")

                file.write("|\r")

                if score == 0:
                    issues[mpn] = "Not found in Mouser or Farnell"

            if issues:
                warning_string = "Issues found with the following parts:\n"
                for mpn, issue in issues.items():
                    warning_string += f"* {mpn}:    {issue}\n"
                print(warning_string)
                # WarningDialog(warning_string, "BOM Issues found")
            else:
                print("OK")
                # InfoDialog("No BOM issues found", "Mousearch")


if __name__ == "__main__":
    input_dir = pathlib.Path(sys.argv[1])
    found_projects = list(input_dir.rglob("*.kicad_pro"))
    assert len(found_projects) == 1, f"Multiple projects found: {found_projects}"
    top_level_schematic = found_projects[0].with_suffix(".kicad_sch")
    print(f"Generating BOM for {top_level_schematic}")
    
    x = Mousearch(sys.argv[1], sys.argv[2], sys.argv[3])
    x.generate_bom(top_level_schematic=top_level_schematic)
