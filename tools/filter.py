# This file is part of the EESSI build-and-deploy bot,
# see https://github.com/EESSI/eessi-bot-software-layer
#
# The bot helps with requests to add software installations to the
# EESSI software layer, see https://github.com/EESSI/software-layer
#
# author: Thomas Roeblitz (@trz42)
#
# license: GPLv2
#
import re

from collections import namedtuple
from pyghee.utils import log


FILTER_COMPONENTS = ['architecture', 'instance', 'job', 'repository']

Filter = namedtuple('Filter', ('component', 'pattern'))


class EESSIBotActionFilter:
    def __init__(self):
        """
        EESSIBotActionFilter constructor
        """

        self.action_filters = []

    def clear_all(self):
        self.action_filters = []

    def add_filter(self, component, pattern):
        """
        Adds a filter

        Args:
            component (string): any prefix of 'architecture', 'instance', 'job' or 'repository'
            pattern (string): regex that is applied to a string representing the component
        """
        # check if component is supported
        full_component = None
        for cis in FILTER_COMPONENTS:
            if cis.startswith(component):
                full_component = cis
                break
        if full_component:
            log(f"processing component {component}")
            # if full_component == architecture replace - with / in pattern
            if full_component == 'architecture':
                pattern = pattern.replace('-', '/')
            self.action_filters.append(Filter(full_component, pattern))
        else:
            log(f"component {component} is unknown")

    def remove_filter(self, component, pattern):
        """
        Removes all elements matching the filter given by (component, pattern)

        Args:
            component (string): any prefix of 'architecture', 'instance', 'job' or 'repository'
            pattern (string): regex that is applied to a string representing the component
        """
        index = 0
        for _filter in self.action_filters:
            if _filter.component.startswith(component) and pattern == _filter.pattern:
                log(f"removing filter ({_filter.component}, {pattern})")
                self.action_filters.pop(index)
            else:
                index += 1

    def to_string(self):
        """
        Convert filters to string
        """
        filter_string = ''
        for _filter in self.action_filters:
            cm = _filter.component
            re = _filter.pattern
            filter_string += f"{cm}:{re}\n"
        return filter_string

    def check_filters(self, context):
        """
        Checks filters for a given context which is defined by one to four
        components (architecture, instance, job, repository)

        Args:
            context (dict) : dictionary that maps component to value

        Returns:
            True if all defined filters match corresponding component in given
            context
        """
        # if no filters are defined we return True
        if len(self.action_filters) == 0:
            return True

        # we have at least one filter which has to match or we return False
        check = False

        # examples:
        #   arch:intel instance:AWS --> rebuild for all repos for intel architectures on AWS
        #   arch:generic --> rebuild for all repos for generic architectures anywhere
        #   repository:nessi.no-2022.11 --> disable all builds for nessi.no-2022.11
        # we iterate over all defined filters
        for af in self.action_filters:
            if af.component in context:
                value = context[af.component]
                # replace - with / in architecture component
                if af.component == 'architecture':
                    value = value.replace('-', '/')
                if re.search(af.pattern, value):
                    # if the pattern of the filter matches
                    check = True
                else:
                    check = False
                    break
        return check