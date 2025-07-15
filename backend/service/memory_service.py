import json
import os
from datetime import datetime

# Verzeichnis für Memory-Dateien
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
MEMORY_DIR = os.path.join(BASE_DIR, 'project_memory')
os.makedirs(MEMORY_DIR, exist_ok=True)


def _append_memory(entry: dict):
    """Schreibt einen JSON-Eintrag als neue Zeile in memory.log"""
    file = os.path.join(MEMORY_DIR, 'memory.log')
    with open(file, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry, default=str) + '\n')


def save_load_case(load_case):
    """Speichert einen einzelnen LoadCase ins Memory-Log"""
    entry = {
        'timestamp': datetime.utcnow().isoformat(),
        'type': 'load_case',
        'data': load_case.__dict__
    }
    _append_memory(entry)


def save_sprungmass(sprungmass: float):
    """Speichert das Sprungmaß ins Memory-Log"""
    entry = {
        'timestamp': datetime.utcnow().isoformat(),
        'type': 'sprungmass',
        'data': {'sprungmass': sprungmass}
    }
    _append_memory(entry)


def save_combination(combination: dict):
    """Speichert das Ergebnis der Lastenkombination ins Memory-Log"""
    entry = {
        'timestamp': datetime.utcnow().isoformat(),
        'type': 'combination',
        'data': combination
    }
    _append_memory(entry)


def save_snapshot(snapshot: dict):
    """Speichert einen vollständigen Snapshot aller Eingabedaten ins Memory-Log"""
    entry = {
        'timestamp': datetime.utcnow().isoformat(),
        'type': 'snapshot',
        'data': snapshot
    }
    _append_memory(entry)
