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

# Standard library imports
from collections import namedtuple
import re

# Third party imports (anything installed into the local Python environment)
from pyghee.utils import log

# Local application imports (anything from EESSI/eessi-bot-software-layer)
# (none yet)


# NOTE because one can use any prefix of one of the four components below to
# define a filter, we need to make sure that no two filters share the same
# prefix OR we have to change the handling of filters.
FILTER_COMPONENT_ARCH = 'architecture'
FILTER_COMPONENT_INST = 'instance'
FILTER_COMPONENT_JOB = 'job'
FILTER_COMPONENT_REPO = 'repository'
FILTER_COMPONENTS = [FILTER_COMPONENT_ARCH, FILTER_COMPONENT_INST, FILTER_COMPONENT_JOB, FILTER_COMPONENT_REPO]

Filter = namedtuple('Filter', ('component', 'pattern'))


class EESSIBotActionFilterError(Exception):
    """
    Exception to be raised when encountering an error in creating or adding a
    filter
    """
    pass


class EESSIBotActionFilter:
    """
    Class for representing a filter that limits in which contexts bot commands
    are applied. A filter contains a list of key:value pairs where the key
    corresponds to a component (see FILTER_COMPONENTS) and the value is a
    pattern used to filter commands based on the context a command is applied to.
    """
    def __init__(self, filter_string):
        """
        EESSIBotActionFilter constructor

        Args:
            filter_string (string): string containing whitespace separated filters

        Raises:
            EESSIBotActionFilterError: raised if caught when adding filter from
                string
            Exception: logged and raised if caught when adding filter from
                string
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
        """
        Clears all filters

        Args:
            No arguments

        Returns:
            None (implicitly)
        """
        self.action_filters = []

    def add_filter(self, component, pattern):
        """
        Adds a filter given by a component and a pattern

        Args:
            component (string): any prefix of known filter components (see
                FILTER_COMPONENTS)
            pattern (string): regular expression pattern that is applied to a
                string representing the component

        Returns:
            None (implicitly)

        Raises:
           EESSIBotActionFilterError: raised if unknown component is provided
                as argument
        """
        # check if component is supported (i.e., it is a prefix of one of the
        # elements in FILTER_COMPONENTS)
        full_component = None
        for cis in FILTER_COMPONENTS:
            # NOTE the below code assumes that no two filter share the same
            # prefix (e.g., 'repository' and 'request' would have the same
            # prefixes 'r' and 're')
            if cis.startswith(component):
                full_component = cis
                break
        if full_component:
            log(f"processing component {component}")
            # replace '-' with '/' in pattern when using 'architecture' filter
            # component (done to make sure that values are comparable)
            if full_component == FILTER_COMPONENT_ARCH:
                pattern = pattern.replace('-', '/')
            self.action_filters.append(Filter(full_component, pattern))
        else:
            log(f"component {component} is unknown")
            raise EESSIBotActionFilterError(f"unknown component={component} in {component}:{pattern}")

    def add_filter_from_string(self, filter_string):
        """
        Adds a filter provided as a string

        Args:
            filter_string (string): filter provided as component:pattern string

        Returns:
            None (implicitly)

        Raises:
           EESSIBotActionFilterError: raised if filter_string does not conform
               to 'component:pattern' format or pattern is empty
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

        Returns:
            None (implicitly)
        """
        index = 0
        for _filter in self.action_filters:
            # NOTE the below code assumes that no two filter share the same
            # prefix (e.g., 'repository' and 'request' would have the same
            # prefixes 'r' and 're')
            if _filter.component.startswith(component) and pattern == _filter.pattern:
                log(f"removing filter ({_filter.component}, {pattern})")
                self.action_filters.pop(index)
            else:
                index += 1

    def to_string(self):
        """
        Convert filters to string

        Args:
            No arguments

        Returns:
            string containing filters separated by whitespace
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
            context (dict) : dictionary that maps components to their value

        Returns:
            True if no filters are defined or all defined filters match
                their corresponding component in the given context
            False if any defined filter does not match its corresponding
                component in the given context
        """
        # if no filters are defined we return True
        if len(self.action_filters) == 0:
            return True

        # we have at least one filter which has to match or we return False
        check = False

        # examples:
        #   filter: 'arch:intel instance:AWS' --> evaluates to True if
        #       context['architecture'] matches 'intel' and if
        #       context['instance'] matches 'AWS'
        #   filter: 'repository:eessi-2023.06' --> evaluates to True if
        #       context['repository'] matches 'eessi-2023.06'

        # we iterate over all defined filters
        for af in self.action_filters:
            if af.component in context:
                value = context[af.component]
                # replace - with / in architecture component
                if af.component == FILTER_COMPONENT_ARCH:
                    value = value.replace('-', '/')
                if re.search(af.pattern, value):
                    # if the pattern of the filter matches
                    check = True
                else:
                    check = False
                    break
        return check
