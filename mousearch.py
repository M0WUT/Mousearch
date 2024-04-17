import pathlib
import re
from datetime import datetime
from itertools import islice
from math import ceil
from time import sleep

import pcbnew

from .common import ErrorDialog, InfoDialog, WarningDialog
from .mouser_api import MouserAPI


# Copied from https://realpython.com/how-to-split-a-python-list-into-chunks/
def batched(iterable, num_per_batch):
    if num_per_batch < 1:
        raise ValueError("Batches must be at least 1 item in size")
    it = iter(iterable)
    while batch := tuple(islice(it, num_per_batch)):
        yield batch


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
            with open(pwd / "api_key.txt", "r") as file:
                api_key = file.readline()
                mouser_api = MouserAPI(api_key)
        except FileNotFoundError:
            ErrorDialog(
                message="Please add a Mouser Search API key in 'api_key.txt' in your Kicad scripting directory",
                title="No API Key found",
            )
            return

        # Have to batch in 30 items per minute to avoid Mouser maximum calls per minute limit
        sub_boms = batched(bom.items(), 30)
        WarningDialog(
            message=f"To avoid Mouser DDOS, this has to be rate limited to 30 items per minute. Expected completion is {ceil(len(bom) / 30)} minutes",
            title="This may take a while...",
        )
        issues = {}
        for sub_bom in sub_boms:
            start_time = datetime.now()
            for mpn, quantity in sub_bom:
                available_quantity = mouser_api.check_for_stock(mpn)
                if available_quantity == -1:
                    issues[mpn] = "Not found at Mouser"
                elif available_quantity < quantity:
                    issues[mpn] = (
                        f"Required: {quantity}, Available: {available_quantity}"
                    )

            time_to_sleep = 65 - (datetime.now() - start_time).seconds
            if time_to_sleep > 0:
                sleep(time_to_sleep)

        if issues:
            warning_string = "Issues found with the following parts:\n"
            for mpn, issue in issues.items():
                warning_string += f"* {mpn}:    {issue}\n"
            WarningDialog(warning_string, "BOM Issues found")
        else:
            InfoDialog("No BOM issues found", "Mousearch")
