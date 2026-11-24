"""A pipeline hypothesis and the chemical reference records associated with it."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Match:
    qid: str
    key: str
    origin: str
    isomeric_smiles: str = ''
    pubchem: tuple[str, ...] = ()
    name: str = ''


@dataclass(frozen=True, slots=True)
class Candidate:
    filename: str
    feature: str
    method: str
    identifier: str
    key: str = ''
    inchi: str = ''
    smiles: str = ''
    name: str = ''
    rank: str = ''
    score: str = ''
    evidence: str = ''
    adduct: str = ''
    pubchem: tuple[str, ...] = ()
    matches: tuple[Match, ...] = ()
    formula: str = ''
