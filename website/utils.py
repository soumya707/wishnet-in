# -*- coding: utf-8 -*-

"""Define helper functions for the application."""

import csv


class AvailablePlans():
    """Define all the available plans."""

    def __init__(self, filepath, **kwds):
        super(AvailablePlans, self).__init__(**kwds)
        self.all_plans = self._get_all_plans_data(filepath)

    def _get_all_plans_data(self, filepath):
        with open(filepath, 'r') as csvfile:
            plan_reader = csv.reader(csvfile)
            # skip header
            next(plan_reader)
            return {row[2]: (row[0], row[3]) for row in plan_reader}
