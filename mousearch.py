import pathlib
import re
from datetime import datetime
from itertools import islice
from math import ceil
from time import sleep
import pathlib

import pcbnew

from .common import ErrorDialog, InfoDialog, WarningDialog
from .mouser_api import MouserAPI
from .farnell_api import FarnellAPI

MOUSER_BIT = 1 << 1
FARNELL_BIT = 1 << 0


class Mousearch:
    def __init__(self, board: pcbnew.BOARD):
        self.board = board
        self.run()

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
        pwd = pathlib.Path(__file__).parent.resolve()
        try:
            with open(pwd / "mouser_key.txt", "r") as file:
                api_key = file.readline()
                mouser_api = MouserAPI(api_key)
        except FileNotFoundError:
            ErrorDialog(
                message=f"Please add a Mouser Search API key in 'mouser_key.txt' in {pathlib.Path(__file__).parent.resolve()}",
                title="No API Key found",
            )
            return

        try:
            with open(pwd / "farnell_key.txt", "r") as file:
                api_key = file.readline()
                farnell_api = FarnellAPI(api_key)
        except FileNotFoundError:
            ErrorDialog(
                message=f"Please add an element14 API key in 'farnell_key.txt' in {pathlib.Path(__file__).parent.resolve()}",
                title="No API Key found",
            )
            return

        # Have to batch in 30 items per minute to avoid Mouser maximum calls per minute limit
        WarningDialog(
            message=f"To avoid Mouser DDOS, this has to be rate limited to 30 items per minute. Expected completion is {ceil(len(bom) / 30)} minutes and will cause Kicad to freeze until complete.",
            title="This may take a while...",
        )
        issues = {}

        found_parts = {}

        for mpn, quantity in bom.items():
            score = 0
            # Check Mouser
            if mouser_api.check_for_stock(mpn) >= quantity:
                score += MOUSER_BIT

            # Check Farnell
            if farnell_api.check_for_stock(mpn) >= quantity:
                score += FARNELL_BIT

            found_parts[mpn] = score
            sleep(2)
        
        # Print report in sorted order
        with open(pathlib.Path(__file__).parent.resolve() / "results.md", "w") as file:
            file.write("| MPN | Mouser | Farnell |\r")
            file.write("| --- | --- | --- |\r")
            for mpn, score in sorted(found_parts.items(), key=lambda item: item[1]):
                
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
                WarningDialog(warning_string, "BOM Issues found")
            else:
                InfoDialog("No BOM issues found", "Mousearch")
