# Tests for functions defined in 'tools/filter.py' of the EESSI
# build-and-deploy bot, see https://github.com/EESSI/eessi-bot-software-layer
#
# The bot helps with requests to add software installations to the
# EESSI software layer, see https://github.com/EESSI/software-layer
#
# author: Thomas Roeblitz (@trz42)
#
# license: GPLv2
#

# Standard library imports

# Third party imports (anything installed into the local Python environment)
import pytest

# Local application imports (anything from EESSI/eessi-bot-software-layer)
from tools.filter import EESSIBotActionFilter, EESSIBotActionFilterError


def test_empty_action_filter():
    af = EESSIBotActionFilter("")
    expected = ''
    actual = af.to_string()
    assert expected == actual


def test_add_single_action_filter():
    af = EESSIBotActionFilter("")
    component = 'arch'
    pattern = '.*intel.*'
    af.add_filter(component, pattern)
    expected = "architecture:.*intel.*"
    actual = af.to_string()
    assert expected == actual


def test_add_non_supported_component():
    af = EESSIBotActionFilter("")
    component = 'machine'
    pattern = '.*intel.*'
    with pytest.raises(Exception) as err:
        af.add_filter(component, pattern)
    assert err.type == EESSIBotActionFilterError


def test_check_matching_empty_filter():
    af = EESSIBotActionFilter("")
    expected = ''
    actual = af.to_string()
    assert expected == actual

    context = {"arch": "foo"}
    actual = af.check_filters(context)
    expected = True
    assert expected == actual


def test_check_matching_simple_filter():
    af = EESSIBotActionFilter("")
    component = 'arch'
    pattern = '.*intel.*'
    af.add_filter(component, pattern)
    expected = f"architecture:{pattern}"
    actual = af.to_string()
    assert expected == actual

    context = {"architecture": "x86_64/intel/cascadelake"}
    actual = af.check_filters(context)
    expected = True
    assert expected == actual


@pytest.fixture
def complex_filter():
    af = EESSIBotActionFilter("")
    component1 = 'arch'
    pattern1 = '.*intel.*'
    af.add_filter(component1, pattern1)
    component2 = 'repo'
    pattern2 = 'nessi.no-2022.*'
    af.add_filter(component2, pattern2)
    component3 = 'i'
    pattern3 = '[aA]'
    af.add_filter(component3, pattern3)
    yield af


def test_create_complex_filter(complex_filter):
    expected = "architecture:.*intel.*"
    expected += " repository:nessi.no-2022.*"
    expected += " instance:[aA]"
    actual = complex_filter.to_string()
    assert expected == actual


def test_match_empty_context(complex_filter):
    context = {}
    expected = False
    actual = complex_filter.check_filters(context)
    assert expected == actual


def test_match_architecture_context(complex_filter):
    context = {"architecture": "x86_64/intel/cascadelake"}
    expected = True
    actual = complex_filter.check_filters(context)
    assert expected == actual


def test_match_architecture_job_context(complex_filter):
    context = {"architecture": "x86_64/intel/cascadelake", "job": 1234}
    expected = True
    actual = complex_filter.check_filters(context)
    assert expected == actual


def test_non_match_architecture_repository_context(complex_filter):
    context = {"architecture": "x86_64/intel/cascadelake", "repository": "EESSI"}
    expected = False
    actual = complex_filter.check_filters(context)
    assert expected == actual


@pytest.fixture
def arch_filter_slash_syntax():
    af = EESSIBotActionFilter("")
    component1 = 'arch'
    pattern1 = '.*/intel/.*'
    af.add_filter(component1, pattern1)
    yield af


def test_match_architecture_syntax_slash(arch_filter_slash_syntax):
    context = {"architecture": "x86_64/intel/cascadelake", "repository": "EESSI"}
    expected = True
    actual = arch_filter_slash_syntax.check_filters(context)
    assert expected == actual

    context = {"architecture": "x86_64-intel-cascadelake"}
    expected = True
    actual = arch_filter_slash_syntax.check_filters(context)
    assert expected == actual


@pytest.fixture
def arch_filter_dash_syntax():
    af = EESSIBotActionFilter("")
    component1 = 'arch'
    pattern1 = '.*-intel-.*'
    af.add_filter(component1, pattern1)
    yield af


def test_match_architecture_syntax_dash(arch_filter_dash_syntax):
    context = {"architecture": "x86_64-intel-cascadelake", "repository": "EESSI"}
    expected = True
    actual = arch_filter_dash_syntax.check_filters(context)
    assert expected == actual

    context = {"architecture": "x86_64/intel-cascadelake"}
    expected = True
    actual = arch_filter_dash_syntax.check_filters(context)
    assert expected == actual
