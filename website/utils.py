# -*- coding: utf-8 -*-

"""Define helper functions for the application."""


class ActivePlan():
    """Define basic functionality for active plan of the user."""

    def __init__(self, mqs_name, **kwds):
        super(ActivePlan, self).__init__(**kwds)
        self._mqs_name = mqs_name
        # TODO: obtain data from cache
        self.name = self._get_name()
        self.price = self._get_price()

    def _get_name(self):
        """Get the registered name for the plan."""
        pass

    def _get_price(self):
        """Get the price for the plan."""
        pass
