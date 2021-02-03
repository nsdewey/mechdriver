"""
  Functions used for handling and comparing geometries
"""

import numpy
import automol


# Various checks and assessments for geometries
def is_atom_closest_to_bond_atom(zma, idx_rad, bond_dist):
    """ Check to see whether the radical atom is still closest to the bond
        formation site.
    """
    geo = automol.zmat.geometry(zma)
    atom_closest = True
    for idx, _ in enumerate(geo):
        if idx < idx_rad:
            distance = automol.geom.distance(geo, idx, idx_rad)
            if distance < bond_dist-0.01:
                atom_closest = False
                # print('idx test:', idx, distance, bond_dist)
    return atom_closest


def calc_rxn_angle(ts_zma, frm_bnd_keys, brk_bnd_keys, rxn_class):
    """ Calculate the angle over a forming-and-breaking bond
    """

    angle = None
    if 'abstraction' in rxn_class or 'addition' in rxn_class:
        if frm_bnd_keys and brk_bnd_keys:

            ang_atms = [0, 0, 0]
            cent_atm = list(set(brk_bnd_keys) & set(frm_bnd_keys))
            if cent_atm:
                ang_atms[1] = cent_atm[0]
                for idx in brk_bnd_keys:
                    if idx != ang_atms[1]:
                        ang_atms[0] = idx
                for idx in frm_bnd_keys:
                    if idx != ang_atms[1]:
                        ang_atms[2] = idx

                geom = automol.zmat.geometry(ts_zma)
                angle = automol.geom.central_angle(
                    geom, *ang_atms)

    return angle
