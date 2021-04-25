# -*- coding: utf-8 -*-
#  Copyright (c) 2020. Distributed under the terms of the MIT License.
from copy import deepcopy
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional

import numpy as np
from monty.json import MSONable
from pydefect.util.coords import pretty_coords
from tabulate import tabulate
from vise.util.mix_in import ToJsonFileMixIn
from vise.util.typing import Coords


printed_orbital_weight_threshold = 0.1


@dataclass
class BandEdgeEigenvalues(MSONable, ToJsonFileMixIn):
    # [spin, k-idx, band-idx] = energy, occupation
    energies_and_occupations: List[List[List[List[float]]]]
    kpt_coords: List[Tuple[float, float, float]]
    lowest_band_index: int


def pretty_orbital(orbitals: Dict[str, List[float]]):
    """
    :param orbitals: An example is {"Mn": [0.5, 0.4, 0.01]} (no f-orbital)
    :return: "Mn-s: 0.50, Mn-p: 0.40"
    """
    orbital_infos = []
    for elem, orbs in orbitals.items():
        for orb_name, weight in zip(["s", "p", "d", "f"], orbs):
            if weight > printed_orbital_weight_threshold:
                orbital_infos.append(f"{elem}-{orb_name}: {weight:.2f}")
    return ", ".join(orbital_infos)


@dataclass
class OrbitalInfo(MSONable):
    """Note that this is code and its version dependent quantities. """
    energy: float  # max eigenvalue
    # {"Mn": [0.01, ..], "O": [0.03, 0.5]},
    # where lists contain s, p, d, (f) orbital components.
    orbitals: Dict[str, List[float]]
    occupation: float
    participation_ratio: float = None


@dataclass
class BandEdgeOrbitalInfos(MSONable, ToJsonFileMixIn):
    orbital_infos: List[List[List["OrbitalInfo"]]]  # [spin, k-idx, band-idx]
    kpt_coords: List[Coords]
    kpt_weights: List[float]
    lowest_band_index: int
    fermi_level: float

    @property
    def energies_and_occupations(self) -> List[List[List[List[float]]]]:
        result = np.zeros(np.shape(self.orbital_infos) + (2,))
        for i, x in enumerate(self.orbital_infos):
            for j, y in enumerate(x):
                for k, z in enumerate(y):
                    result[i][j][k] = [z.energy, z.occupation]
        return result.tolist()

    def __str__(self):
        return "\n".join([" -- band-edge orbitals info",
                          "K-points info",
                          self._kpt_block,
                          "",
                          "Band info near band edges",
                          self._band_block])

    @property
    def _band_block(self):
        band_block = [["Index", "Kpoint index", "Energy", "Occupation",
                       "P-ratio", "Orbital"]]
        for orbital_info in self.orbital_infos:
            max_idx, min_idx = self._band_idx_range(orbital_info)

            for band_idx in range(min_idx, max_idx):
                # Need to start from 1
                actual_band_idx = band_idx + self.lowest_band_index + 1
                for kpt_idx, orb_info in enumerate(orbital_info[band_idx], 1):
                    energy = f"{orb_info.energy :5.2f}"
                    occupation = f"{orb_info.occupation:4.1f}"
                    p_ratio = f"{orb_info.participation_ratio:4.1f}"
                    orbs = pretty_orbital(orb_info.orbitals)
                    band_block.append([actual_band_idx, kpt_idx, energy,
                                       occupation, p_ratio, orbs])
                band_block.append(["--"])
            band_block.append("")
        return tabulate(band_block, tablefmt="plain")

    @property
    def _kpt_block(self):
        kpt_block = [["Index", "Coords", "Weight"]]
        for index, (kpt_coord, kpt_weight) in enumerate(
                zip(self.kpt_coords, self.kpt_weights), 1):
            coord = pretty_coords(kpt_coord)
            weight = f"{kpt_weight:4.3f}"
            kpt_block.append([index, coord, weight])
        return tabulate(kpt_block, tablefmt="plain")

    @staticmethod
    def _band_idx_range(orbital_info: List[List[OrbitalInfo]]
                        ) -> Tuple[int, int]:
        orbital_info = np.array(orbital_info).T
        middle_idx = int(len(orbital_info) / 2)
        for idx, (former, latter) in enumerate(
                zip(orbital_info[1:], orbital_info[-1])):
            occu_diff = former.occupation - latter.occupation
            # determine the band_idx where the occupation changes largely.
            if occu_diff > 0.1:
                middle_idx = idx + 1
                break
        max_idx = min(middle_idx + 3, len(orbital_info))
        min_idx = max(middle_idx - 3, 0)
        return max_idx, min_idx


def is_any_part_occ(x: OrbitalInfo, y: OrbitalInfo):
    return (min(x.occupation, (1.0 - x.occupation)) > 0.01
            or min(y.occupation, (1.0 - y.occupation)) > 0.01)


@dataclass
class LocalizedOrbital(MSONable):
    band_idx: int
    ave_energy: float
    occupation: float
    orbitals: Dict[str, List[float]]
    participation_ratio: Optional[float] = None
    radius: Optional[float] = None
    center: Optional[Coords] = None


@dataclass
class EdgeInfo(MSONable):
    band_idx: int
    kpt_coord: Coords
    orbital_info: "OrbitalInfo"

    @property
    def orbitals(self):
        return self.orbital_info.orbitals

    @property
    def energy(self):
        return self.orbital_info.energy

    @property
    def occupation(self):
        return self.orbital_info.occupation

    @property
    def p_ratio(self):
        return self.orbital_info.participation_ratio


@dataclass
class PerfectBandEdgeState(MSONable, ToJsonFileMixIn):
    vbm_info: EdgeInfo
    cbm_info: EdgeInfo

    def __str__(self):
        def show_edge_info(edge_info: EdgeInfo):
            return [edge_info.band_idx,
                    edge_info.energy,
                    f"{edge_info.occupation:5.2f}",
                    pretty_orbital(edge_info.orbital_info.orbitals),
                    pretty_coords(edge_info.kpt_coord)]

        return tabulate([
            ["", "Index", "Energy", "Occupation", "Orbitals", "K-point coords"],
            ["VBM"] + show_edge_info(self.vbm_info),
            ["CBM"] + show_edge_info(self.cbm_info)], tablefmt="plain")


@dataclass
class BandEdgeState(MSONable):
    vbm_info: EdgeInfo
    cbm_info: EdgeInfo
    vbm_orbital_diff: float
    cbm_orbital_diff: float
    localized_orbitals: List[LocalizedOrbital]

    @property
    def is_shallow(self):
        return self.vbm_info.occupation < 0.7 or self.cbm_info.occupation > 0.3

    def __str__(self):
        def show_edge_info(edge_info: EdgeInfo):
            return [edge_info.band_idx + 1,
                    f"{edge_info.energy:7.3f}",
                    f"{edge_info.p_ratio:5.2f}",
                    f"{edge_info.occupation:5.2f}",
                    pretty_orbital(edge_info.orbital_info.orbitals),
                    pretty_coords(edge_info.kpt_coord)]

        lines = []
        inner_table = [["", "Index", "Energy", "P-ratio", "Occupation",
                        "Orbitals", "K-point coords"],
                       ["VBM"] + show_edge_info(self.vbm_info),
                       ["CBM"] + show_edge_info(self.cbm_info)]
        lines.append(tabulate(inner_table, tablefmt="plain"))

        lines.append("---")
        lines.append("Localized Orbital(s)")
        inner_table = [["Index", "Energy", "P-ratio", "Occupation", "Orbitals"]]
        for lo in self.localized_orbitals:
            pr = f"{lo.participation_ratio:5.2f}" \
                if lo.participation_ratio else "None"
            inner_table.append([lo.band_idx + 1,
                                f"{lo.ave_energy:7.3f}",
                                pr,
                                f"{lo.occupation:5.2f}",
                                pretty_orbital(lo.orbitals)])
        lines.append(tabulate(inner_table, tablefmt="plain"))
        return "\n".join(lines)


@dataclass
class BandEdgeStates(MSONable, ToJsonFileMixIn):
    states: List[BandEdgeState]  # by spin.

    @property
    def is_shallow(self):
        if any([i.is_shallow for i in self.states]):
            return True
        return False

    @property
    def band_indices_for_parchgs(self):
        result = set()
        for state in self.states:
            result.add(state.vbm_info.band_idx)
            for lo in state.localized_orbitals:
                result.add(lo.band_idx)
            result.add(state.cbm_info.band_idx)

        # Increment index by 1 as VASP band index begins from 1.
        return sorted([i + 1 for i in result])

    def __str__(self):
        lines = [" -- band-edge states info"]
        for spin, state in zip(["up", "down"], self.states):
            lines.append(f"Spin-{spin}")
            lines.append(state.__str__())
            lines.append("")

        return "\n".join(lines)


