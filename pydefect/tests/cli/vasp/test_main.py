# -*- coding: utf-8 -*-
#  Copyright (c) 2020. Distributed under the terms of the MIT License.
from argparse import Namespace
from pathlib import Path

from pymatgen import Composition

from pydefect.cli.vasp.main import parse_args
from pydefect.defaults import defaults


def test_unitcell(mocker):
    mock = mocker.patch("pydefect.cli.vasp.main.Vasprun")
    mock_outcar = mocker.patch("pydefect.cli.vasp.main.Outcar")
    parsed_args = parse_args(["u",
                              "-vb", "vasprun.xml",
                              "-ob", "OUTCAR-1",
                              "-od", "OUTCAR-2"])
    # func is a pointer so need to point the same address.
    expected = Namespace(
        vasprun_band=mock.return_value,
        outcar_band=mock_outcar.return_value,
        outcar_dielectric=mock_outcar.return_value,
        func=parsed_args.func,
    )
    assert parsed_args == expected
    mock.assert_called_once_with("vasprun.xml")
    mock_outcar.assert_any_call("OUTCAR-1")
    mock_outcar.assert_called_with("OUTCAR-2")


def test_make_poscars_wo_options():
    parsed_args = parse_args(["mp",
                              "-e", "Mg", "O"])
    expected = Namespace(
        elements=["Mg", "O"],
        e_above_hull=defaults.e_above_hull,
        func=parsed_args.func)
    assert parsed_args == expected


def test_make_poscars_w_options():
    parsed_args = parse_args(["mp",
                              "-e", "Mg", "O",
                              "--e_above_hull", "0.1"])
    expected = Namespace(
        elements=["Mg", "O"],
        e_above_hull=0.1,
        func=parsed_args.func)
    assert parsed_args == expected


def test_cpd_wo_options():
    parsed_args = parse_args(["cpd",
                              "-d", "Mg", "O"])
    expected = Namespace(
        vasp_dirs=[Path("Mg"), Path("O")],
        target=None,
        func=parsed_args.func)
    assert parsed_args == expected


def test_cpd_w_options():
    parsed_args = parse_args(["cpd",
                              "-d", "Mg", "O",
                              "-t", "MgO"])
    expected = Namespace(
        vasp_dirs=[Path("Mg"), Path("O")],
        target=Composition("MgO"),
        func=parsed_args.func)
    assert parsed_args == expected


def test_make_supercell_wo_options(mocker):
    mock = mocker.patch("pydefect.cli.vasp.main.IStructure")
    parsed_args = parse_args(["s"])
    # func is a pointer so need to point the same address.
    expected = Namespace(
        unitcell=mock.from_file.return_value,
        matrix=None,
        min_num_atoms=50,
        max_num_atoms=300,
        func=parsed_args.func,
    )
    assert parsed_args == expected
    mock.from_file.assert_called_once_with("POSCAR")


def test_make_supercell_w_options(mocker):
    mock = mocker.patch("pydefect.cli.vasp.main.IStructure")
    parsed_args = parse_args(["s",
                              "-p", "POSCAR-tmp",
                              "--matrix", "1", "2", "3",
                              "--min_num_atoms", "1000",
                              "--max_num_atoms", "2000"])
    # func is a pointer so need to point the same address.
    expected = Namespace(
        unitcell=mock.from_file.return_value,
        matrix=[1, 2, 3],
        min_num_atoms=1000,
        max_num_atoms=2000,
        func=parsed_args.func,
    )
    assert parsed_args == expected
    mock.from_file.assert_called_once_with("POSCAR-tmp")


def test_make_defect_set_wo_options():
    parsed_args = parse_args(["ds"])
    expected = Namespace(
        oxi_states=None,
        dopants=None,
        kwargs=None,
        func=parsed_args.func,
    )
    assert parsed_args == expected


def test_make_defect_set_w_options():
    parsed_args = parse_args(["ds",
                              "-o", "He", "1",
                              "-d", "Li",
                              "-k", "Li_H1", "Va_H1_0"])
    expected = Namespace(
        oxi_states=["He", "1"],
        dopants=["Li"],
        kwargs=["Li_H1", "Va_H1_0"],
        func=parsed_args.func,
    )
    assert parsed_args == expected


def test_make_defect_entries():
    parsed_args = parse_args(["de"])
    expected = Namespace(
        func=parsed_args.func,
    )
    assert parsed_args == expected



"""
TODO
-

DONE
"""