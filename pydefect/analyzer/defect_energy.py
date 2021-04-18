# -*- coding: utf-8 -*-
#  Copyright (c) 2020. Distributed under the terms of the MIT License.
from copy import deepcopy
from dataclasses import dataclass, InitVar
from itertools import groupby, combinations
from typing import List, Dict, Optional, Tuple

import numpy as np
from monty.json import MSONable
from monty.serialization import loadfn
from pydefect.util.prepare_names import prettify_names
from scipy.spatial import HalfspaceIntersection
from vise.util.mix_in import ToJsonFileMixIn, ToYamlFileMixIn
from vise.util.string import latexify


@dataclass
class DefectEnergy(MSONable):
    formation_energy: float
    energy_corrections: Dict[str, float]
    is_shallow: Optional[bool] = None

    @property
    def total_correction(self) -> float:
        return sum([v for v in self.energy_corrections.values()])

    def energy(self, with_correction):
        if with_correction:
            return self.formation_energy + self.total_correction
        return self.formation_energy


@dataclass
class DefectEnergyInfo(MSONable, ToYamlFileMixIn):
    name: str
    charge: int
    atom_io: Dict[str, int]
    defect_energy: DefectEnergy

    def to_yaml(self) -> str:
        lines = [f"name: {self.name}",
                 f"charge: {self.charge}",
                 f"formation_energy: {self.defect_energy.formation_energy}",
                 f"atom_io:"]
        for k, v in self.atom_io.items():
            lines.append(f"  {k}: {v}")
        lines.append(f"energy_corrections:")
        for k, v in self.defect_energy.energy_corrections.items():
            lines.append(f"  {k}: {v}")
        is_shallow = "" if self.defect_energy.is_shallow is None \
            else self.defect_energy.is_shallow
        lines.append(f"is_shallow: {is_shallow}")
        return "\n".join(lines)

    @classmethod
    def from_yaml(cls, filename: str = "defect_energy_info.yaml"
                  ) -> "DefectEnergyInfo":
        d = loadfn(filename)
        if d["atom_io"] is None:
            d["atom_io"] = {}
        return cls(d.pop("name"), d.pop("charge"), d.pop("atom_io"),
                   DefectEnergy(**d))


@dataclass
class DefectEnergies(MSONable):
    atom_io: Dict[str, int]
    charges: List[int]
    defect_energies: List[DefectEnergy]

    def to_yaml(self):
        pass


@dataclass
class DefectEnergySummary(MSONable, ToJsonFileMixIn):
    title: str
    defect_energies: Dict[str, "DefectEnergies"]
    rel_chem_pots: Dict[str, Dict[str, float]]
    cbm: float
    supercell_vbm: float
    supercell_cbm: float
    e_min: Optional[float] = 0.0
    e_max: Optional[float] = None
    """ The base Fermi level is set at the VBM."""

    # TODO: when making this class, if all the defect charges show shallow
    # show warning.
    def charge_energies(self,
                        chem_pot_label: str,
                        allow_shallow: bool,
                        with_correction: bool,
                        name_style: Optional[str] = None,
                        ) -> "ChargeEnergies":
        e_max = self.cbm if self.e_max is None else self.e_max
        #TODO: generate logger.info when e_min < supercell_vbm.
        rel_chem_pot = self.rel_chem_pots[chem_pot_label]
        result = {}
        for k, v in self.defect_energies.items():
            x = []
            for c, e in zip(v.charges, v.defect_energies):
                if allow_shallow is False and e.is_shallow is True:
                    continue
                reservoir_e = sum([-diff * rel_chem_pot[elem]
                                  for elem, diff in v.atom_io.items()])
                x.append((c, e.energy(with_correction) + reservoir_e))

            if x:
                result[k] = SingleChargeEnergies(x)

        return ChargeEnergies(prettify_names(result, name_style), self.e_min, e_max)

    @property
    def latexified_title(self):
        return latexify(self.title)


@dataclass
class ChargeEnergies:
    charge_energies_dict: Dict[str, "SingleChargeEnergies"]
    e_min: float
    e_max: float

    def __post_init__(self):
        self.cross_point_dicts = {}
        large_minus_number = -1e4
        half_spaces = []
        for name, ce in self.charge_energies_dict.items():
            for charge, corr_energy in ce.charge_energies:
                half_spaces.append([-charge, 1, -corr_energy])

            half_spaces.append([-1, 0, self.e_min])
            half_spaces.append([1, 0, -self.e_max])
            half_spaces.append([0, -1, large_minus_number])

            feasible_point = np.array([(self.e_min + self.e_max) / 2, -1e3])

            hs = HalfspaceIntersection(np.array(half_spaces), feasible_point)
            boundary_points = []
            inner_cross_points = []
            for intersection in hs.intersections:
                x, y = np.round(intersection, 8)
                if self.e_min + 0.001 < x < self.e_max - 0.001:
                    inner_cross_points.append([x, y])
                elif y > large_minus_number + 1:
                    boundary_points.append([x, y])

            self.cross_point_dicts[name] = CrossPoints(inner_cross_points,
                                                       boundary_points)

    def energy_range(self, space: float) -> List[float]:
        candidates = []
        for cp in self.cross_point_dicts.values():
            candidates.extend(cp.t_all_sorted_points[1])
        return [min(candidates) - space, max(candidates) + space]


@dataclass
class SingleChargeEnergies:
    charge_energies: List[Tuple[int, float]]

    @property
    def transition_levels(self) -> Dict[Tuple[int, int], float]:
        result = {}
        for (c1, e1), (c2, e2) in combinations(self.charge_energies, 2):
            result[(c1, c2)] = - (e1 - e2) / (c1 - c2)
        return result

    def pinning_level(self, e_min, e_max
                      ) -> Tuple[Tuple[float, Optional[int]],
                                 Tuple[float, Optional[int]]]:
        """
        :return: ((Lower pinning, its charge), (Upper pinning, its charge))
        """
        lower_pinning, upper_pinning = float("-inf"), float("inf")
        lower_charge, upper_charge = None, None
        for charge, energy in self.charge_energies:
            if charge == 0:
                continue
            pinning = - energy / charge
            if charge > 0 and pinning > lower_pinning:
                lower_pinning, lower_charge = pinning, charge
            elif pinning < upper_pinning:
                upper_pinning, upper_charge = pinning, charge

        if lower_charge is None or lower_pinning < e_min:
            lower = None
        else:
            lower = (lower_pinning, lower_charge)

        if upper_charge is None or upper_pinning > e_max:
            upper = None
        else:
            upper = (lower_pinning, lower_charge)
        return lower, upper

    def energy_at_ef(self, ef: float) -> Tuple[float, int]:
        """
        :return: (Lowest energy, its charge)
        """
        result_e, result_charge = float("inf"), None
        for charge, energy in self.charge_energies:
            energy = energy + charge * ef
            if energy < result_e:
                result_e, result_charge = energy, charge
        return result_e, result_charge


@dataclass
class CrossPoints:
    inner_cross_points: List[List[float]]  # [Fermi level, energy]
    boundary_points: List[List[float]]

    @property
    def all_sorted_points(self):
        return sorted(self.boundary_points + self.inner_cross_points,
                      key=lambda v: v[0])

    @property
    def t_all_sorted_points(self):
        return np.transpose(np.array(self.all_sorted_points)).tolist()

    @property
    def t_inner_cross_points(self):
        return np.transpose(np.array(self.inner_cross_points)).tolist()

    @property
    def t_boundary_points(self):
        return np.transpose(np.array(self.boundary_points)).tolist()

    @property
    def charges(self) -> List[int]:
        result = []
        for i, j in zip(self.all_sorted_points[:-1], self.all_sorted_points[1:]):
            dx = j[0] - i[0]
            dy = j[1] - i[1]
            result.append(int(round(dy / dx)))
        return result

    @property
    def charge_list(self):
        charges = [None] + self.charges + [None]
        return list(zip(charges[:-1], charges[1:]))

    @property
    def annotated_charge_positions(self):
        result = {}
        for ((x1, y1), (x2, y2)), charge \
                in zip(zip(self.all_sorted_points[:-1],
                           self.all_sorted_points[1:]),
                       self.charges):
            result[charge] = [(x1 + x2) / 2, (y1 + y2) / 2]
        return result

    def __str__(self):
        lines = []
        for point in self.all_sorted_points:
            lines.append(f"{point[0]:12.4f} {point[1]:12.4f}")
        return "\n".join(lines)


