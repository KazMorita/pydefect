# -*- coding: utf-8 -*-
#  Copyright (c) 2020 Kumagai group.
from pandas import DataFrame
from pandas._testing import assert_frame_equal
from pydefect.cli.vasp.create_local_extrema import extrema_coords, \
    VolumetricDataAnalyzeParams, find_inequivalent_coords, \
    make_local_extrema_from_volumetric_data
from pydefect.input_maker.local_extrema import CoordInfo
from pydefect.util.structure_tools import Coordination
from pymatgen.io.vasp import Chgcar, VolumetricData

import numpy as np


def test_make_local_extrema_from_volumetric_data(vasp_files):
    aeccar0 = Chgcar.from_file(str(vasp_files / "NaMgF3_AECCAR0"))
    aeccar2 = Chgcar.from_file(str(vasp_files / "NaMgF3_AECCAR2"))
    aeccar = aeccar0 + aeccar2
    aeccar.write_file("CHGCAR")
    make_local_extrema_from_volumetric_data(aeccar)


def test_find_inequivalent_coords(simple_cubic):

    df = DataFrame([[0.1, 0.0, 0.0, 1.0],
                    [0.0, 0.1, 0.0, 1.0],
                    [0.0, 0.0, 0.1, 1.0],
                    [0.9, 0.0, 0.0, 1.0],
                    [0.0, 0.9, 0.0, 1.0],
                    [0.0, 0.0, 0.9, 1.0]],
                   columns=["a", "b", "c", "value"])
    actual = find_inequivalent_coords(simple_cubic, df)
    expected = CoordInfo(
        site_symmetry="4mm",
        coordination=Coordination({"H": [0.1]}, 0.13, [0]),
        frac_coords=[(0.1, 0.0, 0.0), (0.0, 0.1, 0.0), (0.0, 0.0, 0.1),
                     (0.9, 0.0, 0.0), (0.0, 0.9, 0.0), (0.0, 0.0, 0.9)],
        quantities=[1.0]*6)
    assert actual[0] == expected


def test_extrema_coords(vasp_files, simple_cubic):
    aeccar = VolumetricData(simple_cubic,
                            data={"total": np.array(
                                [[[0.0, 0.0], [-1.0, 0.0]],
                                 [[-1.0, 0.0], [-2.0, -1.0]]])})
    actual = extrema_coords(volumetric_data=aeccar, find_min=True,
                            params=VolumetricDataAnalyzeParams(radius=0.51,
                                                               min_dist=0.01,
                                                               tol=0.01))
    expected = DataFrame([[0.5, 0.5, 0.0, -2.0, -1.25]],
                         columns=["a", "b", "c", "value", "ave_value"])
    assert_frame_equal(actual, expected)
