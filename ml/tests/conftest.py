"""
Shared pytest fixtures / path setup for the club-football ML test-suite.

The ``ml/`` package modules import each other by bare name (``import leagues``,
``import club_features``), so we put ``ml/`` on ``sys.path`` before any test
imports them. Kept tiny and dependency-free (numpy only) so the whole suite runs
in well under a second with no network, no trained artifacts and no file writes.
"""
import os
import sys

ML_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ML_DIR not in sys.path:
    sys.path.insert(0, ML_DIR)
