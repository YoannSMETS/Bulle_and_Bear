"""Shared helpers for the in-process Ingescape agents."""
import json

import ingescape as igs

STR = igs.STRING_T
INT = igs.INTEGER_T
IMP = igs.IMPULSION_T


def make_agent(name, family=None):
    agent = igs.Agent(name, True)
    agent.definition_set_class(name)
    if family:
        agent.set_family(family)
    return agent


def add_inputs(agent, **inputs):
    """add_inputs(agent, key_event=STR, ...)"""
    for name, vtype in inputs.items():
        agent.input_create(name, vtype, None)


def add_outputs(agent, **outputs):
    for name, vtype in outputs.items():
        agent.output_create(name, vtype, None)


def listen(agent, input_name, handler):
    """Calls handler(value) for each update of the input."""
    def _cb(_agent, _iop_type, _name, _value_type, value, _data):
        handler(value)
    agent.observe_input(input_name, _cb, None)


def emit(agent, output_name, payload):
    agent.output_set_string(output_name, json.dumps(payload, ensure_ascii=False, separators=(",", ":")))


def parse(value):
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return None


def map_io(dst_agent, dst_input, src_agent, src_output):
    dst_agent.mapping_add(dst_input, src_agent.name(), src_output)
