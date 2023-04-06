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


class EESSIBotActionFilterError(Exception):
    pass


class EESSIBotActionFilter:
    def __init__(self, filter_string):
        """
        EESSIBotActionFilter constructor

        Args:
            filter_string (string): string containing whitespace separated filters
        """
        self.action_filters = []
        for _filter in filter_string.split():
            try:
                self.add_filter_from_string(_filter)
            except EESSIBotActionFilterError:
                raise
            except Exception as err:
                log(f"Unexpected err={err}, type(err)={type(err)}")
                raise

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
            raise EESSIBotActionFilterError(f"unknown component={component} in {component}:{pattern}")

    def add_filter_from_string(self, filter_string):
        """
        Adds a filter from a string

        Args:
            filter_string (string): filter provided as command:pattern
        """
        _filter_split = filter_string.split(':')
        if len(_filter_split) != 2:
            log(f"filter string '{filter_string}' does not conform to format 'component:pattern'")
            raise EESSIBotActionFilterError(f"filter '{filter_string}' does not conform to format 'component:pattern'")
        if len(_filter_split[1]) == 0:
            log(f"pattern in filter string '{filter_string}' is empty")
            raise EESSIBotActionFilterError(f"pattern in filter string '{filter_string}' is empty")
        self.add_filter(_filter_split[0], _filter_split[1])

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
        filter_str_list = []
        for _filter in self.action_filters:
            cm = _filter.component
            re = _filter.pattern
            filter_str_list.append(f"{cm}:{re}")
        return " ".join(filter_str_list)

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
