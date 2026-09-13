"""Deliberately faulty reductions of three historical assumptions. Not original code."""
import json
from pathlib import Path


def profile_home(home, profile):
    return Path(home) / 'profiles' / profile


def search_output(payload):
    return payload['matches']


def decode_response(text):
    return {'status': 'parsed', 'value': json.loads(text)}
