"""Utility functions for forch"""

import yaml

from google.protobuf import json_format


def yaml_proto(file_name, proto_func):
    """Load a yaml file into a proto object"""
    with open(file_name) as stream:
        file_dict = yaml.safe_load(stream)
    return json_format.ParseDict(file_dict, proto_func())


def proto_dict(message):
    """Convert a proto message to a standard dict object"""
    return json_format.MessageToDict(message, preserving_proto_field_name=True)


def proto_json(message):
    """Convert a proto message to a json string"""
    return json_format.MessageToJson(message, preserving_proto_field_name=True)


def dict_proto(message, proto_func):
    """Convert a standard dict object to a proto object"""
    return json_format.ParseDict(message, proto_func())