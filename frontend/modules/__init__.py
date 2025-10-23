"""
Modul-System für Berechnungsmodule.
"""

from .base_module import BaseModule
from .module_registry import get_registry, ModuleRegistry

__all__ = ['BaseModule', 'get_registry', 'ModuleRegistry']
