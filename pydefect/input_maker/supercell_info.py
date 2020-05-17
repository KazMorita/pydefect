# -*- coding: utf-8 -*-
#  Copyright (c) 2020. Distributed under the terms of the MIT License.
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass
from pymatgen import IStructure, Element
from monty.json import MSONable
from numpy.linalg import det
from pydefect.util.structure_tools import Distances
from pydefect.database.database import electronegativity, oxidation_state
from vise.util.logger import get_logger


logger = get_logger(__name__)


@dataclass(frozen=True)
class Site(MSONable):
    element: str
    wyckoff_letter: str
    site_symmetry: str
    equivalent_atoms: List[int]


@dataclass(frozen=True)
class SupercellInfo(MSONable):
    structure: IStructure
    space_group: str
    transform_matrix: List[List[int]]
    sites: Dict[str, Site]

    def coords(self, name):
        site = self.sites[name]
        coord = list(self.structure[site.equivalent_atoms[0]].frac_coords)
        distances = Distances(self.structure, coord)
        return distances.coord_distances_and_cutoff()

    @property
    def multiplicity(self):
        return int(round(det(self.transform_matrix)))

    @property
    def _transform_matrix_str(self):
        return '  '.join(str(x) for x in self.transform_matrix)

    def _frac_coords(self, site):
        repr_atom_idx = site.equivalent_atoms[0]
        frac_coords = self.structure[repr_atom_idx].frac_coords
        return "{0[0]:9.7f}  {0[1]:9.7f}  {0[2]:9.7f}".format(frac_coords)

    @staticmethod
    def _stripe_numbers(name):
        return ''.join([i for i in name if i.isalpha()])

    def __str__(self):
        lines = [f"  Space group: {self.space_group}",
                 f"Transformation matrix: {self._transform_matrix_str}",
                 f"Cell multiplicity: {self.multiplicity}", ""]

        for name, site in self.sites.items():
            distances, cutoff = self.coords(name)
            elem = self._stripe_numbers(name)
            lines.append(f"   Irreducible element: {name}")
            lines.append(f"        Wyckoff letter: {site.wyckoff_letter}")
            lines.append(f"         Site symmetry: {site.site_symmetry}")
            lines.append(f"         Cutoff radius: {cutoff}")
            lines.append(f"          Coordination: {distances}")
            lines.append(f"      Equivalent atoms: {site.equivalent_atoms}")
            lines.append(f"Fractional coordinates: {self._frac_coords(site)}")
            lines.append(f"     Electronegativity: {electronegativity(elem)}")
            lines.append(f"       Oxidation state: {oxidation_state(elem)}")
            lines.append("")

        return "\n".join(lines)
