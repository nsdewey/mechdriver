""" es_runners for conformer
"""

import shutil
import numpy
import automol
import elstruct
import autofile
from autofile import fs
from phydat import bnd
from mechanalyzer.inf import thy as tinfo
from mechroutines.es._routines import _util as util
from mechroutines.es._routines._geom import remove_imag
from mechroutines.es import runner as es_runner
from mechroutines.es.runner import qchem_params
from mechlib import filesys
from mechlib.structure import instab
from mechlib.amech_io import printer as ioprinter


# Initial conformer
def initial_conformer(spc_dct_i, spc_info, ini_method_dct, method_dct,
                      ini_cnf_save_fs, cnf_run_fs, cnf_save_fs,
                      instab_save_fs, es_keyword_dct):
    """ determine what to use as the reference geometry for all future runs
    If ini_thy_info refers to geometry dictionary then use that,
    otherwise values are from a hierarchy of:
    running level of theory, input level of theory, inchis.
    From the hierarchy an optimization is performed followed by a check for
    an imaginary frequency and then a conformer file system is set up.
    """

    ini_thy_info = tinfo.from_dct(ini_method_dct)
    thy_info = tinfo.from_dct(method_dct)
    mod_thy_info = tinfo.modify_orb_label(
        thy_info, spc_info)
    mod_ini_thy_info = tinfo.modify_orb_label(
        ini_thy_info, spc_info)
    [kickoff_size, kickoff_backward] = spc_dct_i['kickoff']

    cnf_locs, cnf_path = filesys.mincnf.min_energy_conformer_locators(
        cnf_save_fs, mod_thy_info)
    overwrite = es_keyword_dct['overwrite']
    if not cnf_locs:
        ioprinter.info_message(
            'No energy found in save filesys. Running energy...')
        _run = True
    elif overwrite:
        ioprinter.info_message(
            'User specified to overwrite energy with new run...')
        _run = True
    else:
        _run = False

    if _run:
        ioprinter.info_message('Obtaining some initial guess geometry.')
        geo_init = _obtain_ini_geom(spc_dct_i, ini_cnf_save_fs,
                                    mod_ini_thy_info,
                                    overwrite)

        if geo_init is not None:
            ioprinter.debug_message(
                'Assessing if there are any functional groups',
                'that cause instability')
            ioprinter.debug_message('geo str\n', automol.geom.string(geo_init))

            zma_init = automol.geom.zmatrix(geo_init)

            # Determine if there is an instability, if so return prods
            instab_zmas = automol.reac.instability_product_zmas(zma_init)
            if not instab_zmas:

                # Build a cid and a run fs
                cid = [autofile.schema.generate_new_conformer_id()]
                cnf_run_fs[-1].create(cid)
                run_fs = autofile.fs.run(cnf_run_fs[-1].path(cid))

                if not automol.geom.is_atom(geo_init):
                    geo_found = _optimize_molecule(
                        spc_info, zma_init,
                        method_dct,
                        instab_save_fs,
                        cnf_save_fs, cid,
                        run_fs,
                        overwrite,
                        kickoff_size=kickoff_size,
                        kickoff_backward=kickoff_backward)
                else:
                    geo_found = _optimize_atom(
                        spc_info, zma_init,
                        method_dct,
                        cnf_save_fs, cid,
                        run_fs,
                        overwrite)
            else:
                instab.write_instab2(
                    zma_init, instab_zmas,
                    instab_save_fs, mod_thy_info[1:4],
                    zma_locs=(0,),
                    save_cnf=True)
                geo_found = True
                ioprinter.info_message(
                    'Found functional groups that cause instabilities')
        else:
            geo_found = False
            ioprinter.warning_message(
                'Unable to obtain an initial guess geometry')
    else:
        ioprinter.existing_path('Initial geometry', cnf_path)
        geo_found = True

    return geo_found


def _obtain_ini_geom(spc_dct_i, ini_cnf_save_fs,
                     mod_ini_thy_info, overwrite):
    """ Obtain an initial geometry to be optimized. Checks a hieratchy
        of places to obtain the initial geom.
            (1) Geom dict which is the input from the user
            (2) Geom from inchi
    """

    geo_init = None

    # Obtain geom from thy fs or remove the conformer filesystem if needed
    if not overwrite:
        ini_min_cnf_locs, _ = filesys.mincnf.min_energy_conformer_locators(
            ini_cnf_save_fs, mod_ini_thy_info)
        if ini_min_cnf_locs:
            geo_init = ini_cnf_save_fs[-1].file.geometry.read(ini_min_cnf_locs)
            ioprinter.info_message(
                'Getting inital geometry from inplvl at path',
                '{}'.format(ini_cnf_save_fs[-1].path(ini_min_cnf_locs)))
    else:
        ioprinter.debug_message(
            'Removing original conformer save data for instability')
        for locs in ini_cnf_save_fs[-1].existing():
            cnf_path = ini_cnf_save_fs[-1].path(locs)
            ioprinter.debug_message('Removing {}'.format(cnf_path))
            shutil.rmtree(cnf_path)

    if geo_init is None:
        if 'geo_inp' in spc_dct_i:
            geo_init = spc_dct_i['geo_inp']
            ioprinter.info_message(
                'Getting initial geometry from geom dictionary')

    if geo_init is None:
        geo_init = automol.inchi.geometry(spc_dct_i['inchi'])
        ioprinter.info_message('Getting initial geometry from inchi')

    # Check if the init geometry is connected
    if geo_init is not None:
        if not automol.geom.connected(geo_init):
            geo_init = None

    return geo_init


def _optimize_atom(spc_info, zma_init,
                   method_dct,
                   cnf_save_fs, cnf_locs,
                   run_fs,
                   overwrite):
    """ Deal with an atom separately
    """

    thy_info = tinfo.from_dct(method_dct)
    mod_thy_info = tinfo.modify_orb_label(thy_info, spc_info)
    script_str, kwargs = qchem_params(
        method_dct, job=elstruct.Job.OPTIMIZATION)

    # Call the electronic structure optimizer
    success, ret = es_runner.execute_job(
        job=elstruct.Job.OPTIMIZATION,
        script_str=script_str,
        run_fs=run_fs,
        geo=zma_init,
        spc_info=spc_info,
        thy_info=mod_thy_info,
        overwrite=overwrite,
        **kwargs
    )

    if success:
        ioprinter.info_message('Succesful reference geometry optimization')
        _save_unique_conformer(
            ret, mod_thy_info, cnf_save_fs, cnf_locs,
            zrxn=None, zma_locs=(0,))

    return success


def _optimize_molecule(spc_info, zma_init,
                       method_dct,
                       instab_save_fs,
                       cnf_save_fs, cnf_locs,
                       run_fs,
                       overwrite,
                       kickoff_size=0.1, kickoff_backward=False):
    """ Optimize a proper geometry
    """

    thy_info = tinfo.from_dct(method_dct)
    mod_thy_info = tinfo.modify_orb_label(thy_info, spc_info)
    script_str, kwargs = qchem_params(
        method_dct, job=elstruct.Job.OPTIMIZATION)

    # Call the electronic structure optimizer
    success, ret = es_runner.execute_job(
        job=elstruct.Job.OPTIMIZATION,
        script_str=script_str,
        run_fs=run_fs,
        geo=zma_init,
        spc_info=spc_info,
        thy_info=mod_thy_info,
        overwrite=overwrite,
        **kwargs
    )

    # read the geometry
    if success:
        inf_obj, _, out_str = ret
        geo = elstruct.reader.opt_geometry(inf_obj.prog, out_str)
        zma = elstruct.reader.opt_zmatrix(inf_obj.prog, out_str)
        geo_conn = bool(automol.geom.connected(geo))
    else:
        geo_conn = False

    # If connected, check for imaginary modes and fix them if possible
    if geo_conn:

        # Remove the imaginary mode
        geo, ret = remove_imag(
            geo, ret, spc_info, method_dct,
            run_fs, kickoff_size, kickoff_backward, kickoff_mode=0,
            overwrite=overwrite)

        # Recheck connectivity for imag-checked geometry
        if geo is not None:

            conf_found = True
            if automol.geom.connected(geo):
                ioprinter.info_message(
                    'Saving structure as the first conformer...', newline=1)
                locs = [autofile.schema.generate_new_conformer_id()]
                _save_unique_conformer(
                    ret, mod_thy_info, cnf_save_fs, locs,
                    zrxn=None, zma_locs=(0,))
            else:
                ioprinter.info_message('Saving disconnected species...')
                _, opt_ret = es_runner.read_job(
                    job=elstruct.Job.OPTIMIZATION, run_fs=run_fs)
                instab.write_instab(
                    zma_init, zma,
                    instab_save_fs, mod_thy_info[1:4],
                    opt_ret,
                    zma_locs=(0,),
                    save_cnf=True
                )
        else:
            ioprinter.warning_message('No geom found...', newline=1)
            conf_found = False
    else:
        ioprinter.info_message('Saving disconnected species...')
        conf_found = False
        _, opt_ret = es_runner.read_job(
            job=elstruct.Job.OPTIMIZATION, run_fs=run_fs)
        instab.write_instab(
            zma_init, zma,
            instab_save_fs, mod_thy_info[1:4],
            opt_ret,
            zma_locs=(0,),
            save_cnf=True
        )

    return conf_found


def single_conformer(zma, spc_info, mod_thy_info,
                     cnf_run_fs, cnf_save_fs,
                     script_str, overwrite,
                     retryfail=True, zrxn=None, **kwargs):
    """ generate single optimized geometry to be saved into a
        filesystem
    """

    # Build the filesystem
    locs = [autofile.schema.generate_new_conformer_id()]
    cnf_run_fs[-1].create(locs)
    cnf_run_path = cnf_run_fs[-1].path(locs)
    run_fs = autofile.fs.run(cnf_run_path)

    # Run the optimization
    ioprinter.info_message('Optimizing a single conformer')
    success, ret = es_runner.execute_job(
        job=elstruct.Job.OPTIMIZATION,
        script_str=script_str,
        run_fs=run_fs,
        geo=zma,
        spc_info=spc_info,
        thy_info=mod_thy_info,
        overwrite=overwrite,
        frozen_coordinates=(),
        saddle=bool(zrxn is not None),
        retryfail=retryfail,
        **kwargs
    )

    if success:
        inf_obj, _, out_str = ret
        prog = inf_obj.prog
        method = inf_obj.method
        ene = elstruct.reader.energy(prog, method, out_str)
        geo = elstruct.reader.opt_geometry(prog, out_str)
        zma = elstruct.reader.opt_zmatrix(prog, out_str)
        saved_locs, saved_geos, saved_enes = _saved_cnf_info(
            cnf_save_fs, mod_thy_info)

        if _geo_unique(geo, ene, saved_geos, saved_enes, zrxn=zrxn):
            sym_id = _sym_unique(
                geo, ene, saved_geos, saved_enes)
            if sym_id is None:
                _save_unique_conformer(
                    ret, mod_thy_info, cnf_save_fs, locs,
                    zrxn=zrxn, zma_locs=(0,))
                saved_geos.append(geo)
                saved_enes.append(ene)
                saved_locs.append(locs)

        # Update the conformer trajectory file
        ioprinter.obj('vspace')
        filesys.mincnf.traj_sort(cnf_save_fs, mod_thy_info)


def conformer_sampling(zma, spc_info, thy_info,
                       cnf_run_fs, cnf_save_fs,
                       script_str, overwrite,
                       nsamp_par=(False, 3, 3, 1, 50, 50),
                       tors_names=(),
                       zrxn=None, two_stage=False, retryfail=False,
                       **kwargs):
    """ run sampling algorithm to find conformers
    """

    # Build filesys
    cnf_save_fs[0].create()
    inf_obj = autofile.schema.info_objects.conformer_trunk(0)

    # Set the samples
    nsamp, tors_range_dct = _calc_nsamp(tors_names, nsamp_par, zma, zrxn=zrxn)
    nsamp0 = nsamp
    nsampd = _calc_nsampd(cnf_save_fs, cnf_run_fs)

    tot_samp = nsamp - nsampd
    ioprinter.info_message(
        ' - Number of samples that have been currently run:', nsampd)
    ioprinter.info_message(' - Number of samples requested:', nsamp)

    if nsamp-nsampd > 0:
        ioprinter.info_message(
            'Running {} samples...'.format(nsamp-nsampd), newline=1)
    samp_idx = 1
    while True:
        nsamp = nsamp0 - nsampd
        # Break the while loop if enough sampls completed
        if nsamp <= 0:
            ioprinter.info_message(
                'Requested number of samples have been completed.',
                'Conformer search complete.')
            break

        # Run the conformer sampling
        if nsampd > 0:
            samp_zma, = automol.zmat.samples(zma, 1, tors_range_dct)
        else:
            samp_zma = zma

        bad_geom_count = 0
        geo = automol.zmat.geometry(zma)
        samp_geo = automol.zmat.geometry(samp_zma)
        while (not automol.pot.low_repulsion_struct(geo, samp_geo) and
               bad_geom_count < 1000):
            ioprinter.warning_message('ZMA has high repulsion.', indent=1/2.)
            ioprinter.warning_message(
                'Generating new sample ZMA', indent=1/2., newline=1)
            samp_zma, = automol.zmat.samples(zma, 1, tors_range_dct)
            bad_geom_count += 1
        ioprinter.debug_message('ZMA is fine...', indent=1/2.)

        cid = autofile.schema.generate_new_conformer_id()
        locs = [cid]

        cnf_run_fs[-1].create(locs)
        cnf_run_path = cnf_run_fs[-1].path(locs)
        run_fs = autofile.fs.run(cnf_run_path)

        ioprinter.info_message("Run {}/{}".format(samp_idx, tot_samp))
        tors_names = tuple(tors_range_dct.keys())
        if two_stage and tors_names:
            frozen_coords_lst = ((), tors_names)
            success, ret = es_runner.multi_stage_optimization(
                script_str=script_str,
                run_fs=run_fs,
                geo=samp_zma,
                spc_info=spc_info,
                thy_info=thy_info,
                frozen_coords_lst=frozen_coords_lst,
                overwrite=overwrite,
                saddle=bool(zrxn is not None),
                retryfail=retryfail,
                **kwargs
            )
        else:
            success, ret = es_runner.execute_job(
                job=elstruct.Job.OPTIMIZATION,
                script_str=script_str,
                run_fs=run_fs,
                geo=samp_zma,
                spc_info=spc_info,
                thy_info=thy_info,
                overwrite=overwrite,
                saddle=bool(zrxn is not None),
                retryfail=retryfail,
                **kwargs
            )

        # save function added here
        if success:
            _save_conformer(
                ret, cnf_save_fs, locs, thy_info,
                zrxn=zrxn, orig_ich=spc_info[0])

            nsampd = _calc_nsampd(cnf_save_fs, cnf_run_fs)
            nsampd += 1
            samp_idx += 1
            inf_obj.nsamp = nsampd
            cnf_save_fs[0].file.info.write(inf_obj)
            cnf_run_fs[0].file.info.write(inf_obj)


def _calc_nsamp(tors_names, nsamp_par, zma, zrxn=None):
    """ Determine the number of samples to od
    """

    tors_ranges = tuple((0, 2*numpy.pi) for tors in tors_names)
    tors_range_dct = dict(zip(tors_names, tors_ranges))
    if zrxn is None:
        gra = automol.zmat.graph(zma)
        ntaudof = len(
            automol.graph.rotational_bond_keys(gra, with_h_rotors=False))
    else:
        ntaudof = len(tors_names)
    nsamp = util.nsamp_init(nsamp_par, ntaudof)
    ioprinter.debug_message('tors_names', tors_names)
    ioprinter.debug_message('tors_range_dct', tors_range_dct)
    if not tors_range_dct:
        ioprinter.info_message(
            " - No torsional coordinates. Setting nsamp to 1.")
        nsamp = 1

    return nsamp, tors_range_dct


def _calc_nsampd(cnf_save_fs, cnf_run_fs):
    """ Determine the number of samples completed
    """

    cnf_save_fs[0].create()
    if cnf_save_fs[0].file.info.exists():
        inf_obj_s = cnf_save_fs[0].file.info.read()
        nsampd = inf_obj_s.nsamp
    elif cnf_run_fs[0].file.info.exists():
        inf_obj_r = cnf_run_fs[0].file.info.read()
        nsampd = inf_obj_r.nsamp
    else:
        nsampd = 0

    return nsampd


def _save_conformer(ret, cnf_save_fs, locs, thy_info, zrxn=None,
                    orig_ich=''):
    """ save the conformers that have been found so far
        # Only go through save procedure if conf not in save
        # may need to get geo, ene, etc; maybe make function
    """

    saved_locs, saved_geos, saved_enes = _saved_cnf_info(
        cnf_save_fs, thy_info)

    inf_obj, _, out_str = ret
    prog = inf_obj.prog
    method = inf_obj.method
    ene = elstruct.reader.energy(prog, method, out_str)
    geo = elstruct.reader.opt_geometry(prog, out_str)
    zma = elstruct.reader.opt_zmatrix(prog, out_str)

    # Assess if geometry is properly connected
    viable = _geo_connected(geo, zrxn)
    if viable:
        if zrxn:
            viable = _ts_geo_viable(
                zma, zrxn, cnf_save_fs, thy_info)
        else:
            viable = _inchi_are_same(orig_ich, geo)

    # Determine uniqueness of conformer, save if needed
    if viable:
        if _geo_unique(geo, ene, saved_geos, saved_enes, zrxn):
            # iso check breaks because of zma location
            # if _is_proper_isomer(cnf_save_fs, zma):
            sym_id = _sym_unique(
                geo, ene, saved_geos, saved_enes)
            if sym_id is None:
                _save_unique_conformer(
                    ret, thy_info, cnf_save_fs,
                    locs, zrxn=zrxn)
            else:
                sym_locs = saved_locs[sym_id]
                _save_sym_indistinct_conformer(
                    geo, cnf_save_fs, locs, sym_locs)

        # Update the conformer trajectory file
        ioprinter.obj('vspace')
        filesys.mincnf.traj_sort(cnf_save_fs, thy_info)


def _geo_connected(geo, rxn):
    """ Assess if geometry is connected. Right now only works for
        minima
    """

    # Determine connectivity (only for minima)
    if rxn is not None:
        gra = automol.geom.graph(geo)
        conns = automol.graph.connected_components(gra)
        lconns = len(conns)
    else:
        lconns = 1

    # Check connectivity
    if lconns == 1:
        connected = True
    else:
        ioprinter.bad_conformer('disconnected')
        connected = False

    return connected


def _geo_unique(geo, ene, seen_geos, seen_enes, zrxn=None):
    """ Assess if a geometry is unique to saved geos

        Need to pass the torsions
    """

    if zrxn is None:
        check_dct = {'dist': 0.3, 'tors': None}
    else:
        check_dct = {'dist': 0.3}

    if automol.util.value_similar_to(ene, seen_enes, 2.e-5):
        unique, _ = automol.geom.is_unique(
            geo, seen_geos, check_dct=check_dct)
    else:
        unique = False
    if not unique:
        ioprinter.bad_conformer('not unique')

    return unique


def _inchi_are_same(orig_ich, geo):
    """ Assess if a geometry has the same connectivity to
     saved geos evaluated in temrs of inchi
    """
    same = False
    ich = automol.geom.inchi(geo)
    assert automol.inchi.is_complete(orig_ich), (
        'the inchi {} orig_ich is not complete'.format(orig_ich))
    if ich == orig_ich:
        same = True
    if not same:
        ioprinter.warning_message(
            " - new inchi {} not the same as old {}".format(ich, orig_ich))

    return same


def _check_old_inchi(orig_ich, seen_geos, saved_locs, cnf_save_fs):
    """
    This assumes you already have bad geos in your save
    """
    for i, geoi in enumerate(seen_geos):
        if not orig_ich == automol.geom.inchi(geoi):
            smi = automol.geom.smiles(geoi)
            ioprinter.error_message(
                'inchi do not match for {} at {}'.format(
                    smi, cnf_save_fs[-1].path(saved_locs[i])))


def _sym_unique(geo, ene, saved_geos, saved_enes, ethresh=1.0e-5):
    """ Check if a conformer is symmetrically distinct from the
        existing conformers in the filesystem
    """

    sym_idx = None
    if not automol.util.value_similar_to(ene, saved_enes, ethresh):
        _, sym_idx = automol.geom.is_unique(
            geo, saved_geos, check_dct={'coulomb': None})

    if sym_idx is not None:
        ioprinter.warning_message(' - Structure is not symmetrically unique.')

    return sym_idx


def _is_proper_isomer(cnf_save_fs, zma):
    """ Check if geom is the same isomer as those in the filesys
    """
    vma = automol.zmat.var_(zma)
    if cnf_save_fs[0].file.vmatrix.exists():
        exist_vma = cnf_save_fs[0].file.vmatrix.read()
        if vma != exist_vma:
            ioprinter.warning_message(
                " - Isomer is not the same as starting isomer. Skipping...")
            proper_isomer = False
        else:
            proper_isomer = True
    else:
        proper_isomer = False

    return proper_isomer


def _ts_geo_viable(zma, zrxn, cnf_save_fs, mod_thy_info, zma_locs=(0,)):
    """ Perform a series of checks to assess the viability
        of a transition state geometry prior to saving
    """

    # Initialize viable
    viable = True

    # Obtain the min-ene zma and bond keys
    _, cnf_save_path = filesys.mincnf.min_energy_conformer_locators(
        cnf_save_fs, mod_thy_info)
    zma_save_fs = fs.zmatrix(cnf_save_path)
    ref_zma = zma_save_fs[-1].file.zmatrix.read(zma_locs)

    # Get the bond dists and calculate the distance of bond being formed
    ref_geo, _ = automol.convert.zmat.geometry(ref_zma)
    cnf_geo, _ = automol.convert.zmat.geometry(zma)
    grxn = automol.reac.relabel_for_geometry(zrxn)

    frm_bnd_keys = automol.reac.forming_bond_keys(grxn)
    brk_bnd_keys = automol.reac.breaking_bond_keys(grxn)

    cnf_dist_lst = []
    ref_dist_lst = []
    bnd_key_lst = []
    cnf_ang_lst = []
    ref_ang_lst = []
    for frm_bnd_key in frm_bnd_keys:
        frm_idx1, frm_idx2 = list(frm_bnd_key)
        cnf_dist = automol.geom.distance(cnf_geo, frm_idx1, frm_idx2)
        ref_dist = automol.geom.distance(ref_geo, frm_idx1, frm_idx2)
        cnf_dist_lst.append(cnf_dist)
        ref_dist_lst.append(ref_dist)
        bnd_key_lst.append(frm_bnd_key)

    for brk_bnd_key in brk_bnd_keys:
        brk_idx1, brk_idx2 = list(brk_bnd_key)
        cnf_dist = automol.geom.distance(cnf_geo, brk_idx1, brk_idx2)
        ref_dist = automol.geom.distance(ref_geo, brk_idx1, brk_idx2)
        cnf_dist_lst.append(cnf_dist)
        ref_dist_lst.append(ref_dist)
        bnd_key_lst.append(brk_bnd_key)

    for frm_bnd_key in frm_bnd_keys:
        for brk_bnd_key in brk_bnd_keys:
            for frm_idx in frm_bnd_key:
                for brk_idx in brk_bnd_key:
                    if frm_idx == brk_idx:
                        idx2 = frm_idx
                        idx1 = list(frm_bnd_key - frozenset({idx2}))[0]
                        idx3 = list(brk_bnd_key - frozenset({idx2}))[0]
                        cnf_ang = automol.geom.central_angle(
                            cnf_geo, idx1, idx2, idx3)
                        ref_ang = automol.geom.central_angle(
                            ref_geo, idx1, idx2, idx3)
                        cnf_ang_lst.append(cnf_ang)
                        ref_ang_lst.append(ref_ang)

    ioprinter.debug_message('bnd_key_list', bnd_key_lst)
    ioprinter.debug_message('conf_dist', cnf_dist_lst)
    ioprinter.debug_message('ref_dist', ref_dist_lst)
    ioprinter.debug_message('conf_angle', cnf_ang_lst)
    ioprinter.debug_message('ref_angle', ref_ang_lst)

    # Set the maximum allowed displacement for a TS conformer
    max_disp = 0.6
    # better to check for bond-form length in bond scission with ring forming
    if 'addition' in grxn.class_:
        max_disp = 0.8
    if 'abstraction' in grxn.class_:
        # this was 1.4 - SJK reduced it to work for some OH abstractions
        max_disp = 1.0

    # Check forming bond angle similar to ini config
    if 'elimination' not in grxn.class_:
        for ref_angle, cnf_angle in zip(ref_ang_lst, cnf_ang_lst):
            if abs(cnf_angle - ref_angle) > .44:
                ioprinter.diverged_ts('angle', ref_angle, cnf_angle)
                viable = False

    symbols = automol.geom.symbols(cnf_geo)
    lst_info = zip(ref_dist_lst, cnf_dist_lst, bnd_key_lst)
    for ref_dist, cnf_dist, bnd_key in lst_info:
        if 'add' in grxn.class_ or 'abst' in grxn.class_:
            bnd_key1, bnd_key2 = min(list(bnd_key)), max(list(bnd_key))
            symb1 = symbols[bnd_key1]
            symb2 = symbols[bnd_key2]

            if bnd_key in frm_bnd_keys:
                # Check if radical atom is closer to some atom
                # other than the bonding atom
                cls = automol.zmat.is_atom_closest_to_bond_atom(
                    zma, bnd_key2, cnf_dist)
                if not cls:
                    ioprinter.diverged_ts('distance', ref_dist, cnf_dist)
                    ioprinter.info_message(
                        ' - Radical atom now has a new nearest neighbor')
                    viable = False
                # check forming bond distance
                if abs(cnf_dist - ref_dist) > max_disp:
                    ioprinter.diverged_ts('distance', ref_dist, cnf_dist)
                    viable = False

            # Check distance relative to equi. bond
            equi_bnd = automol.util.dict_.values_by_unordered_tuple(
                bnd.LEN_DCT, (symb1, symb2), fill_val=0.0)
            displace_from_equi = cnf_dist - equi_bnd
            dchk1 = abs(cnf_dist - ref_dist) > 0.1
            dchk2 = displace_from_equi < 0.2
            if dchk1 and dchk2:
                ioprinter.bad_equil_ts(cnf_dist, equi_bnd)
                viable = False
        else:
            # check forming/breaking bond distance
            # if abs(cnf_dist - ref_dist) > 0.4:
            # max disp of 0.4 causes problems for bond scission w/ ring forming
            # not sure if setting it to 0.3 will cause problems for other cases
            if abs(cnf_dist - ref_dist) > 0.3:
                ioprinter.diverged_ts('distance', ref_dist, cnf_dist)
                viable = False

    return viable


def fs_confs_dict(cnf_save_fs, cnf_save_locs_lst,
                  ini_cnf_save_fs, ini_cnf_save_locs_lst):
    """ Assess which structures from the cnf_save_fs currently exist
        within the ini_cnf_save_fs. Generate a dictionary to connect
        the two
    """

    match_dct = {}
    for ini_locs in ini_cnf_save_locs_lst:

        match_dct[ini_locs] = None
        # Loop over structs in cnf_save, see if they match the current struct
        inigeo =  ini_cnf_save_fs[-1].file.geometry.read(ini_locs)
        inizma = automol.geom.zmatrix(inigeo)
        # inizma =  ini_cnf_save_fs[-1].file.zmatrix.read(ini_locs)
        ini_cnf_save_path = ini_cnf_save_fs[-1].path(ini_locs)
        ioprinter.checking('structures', ini_cnf_save_path)
        for locs in cnf_save_locs_lst:
            geo =  cnf_save_fs[-1].file.geometry.read(locs)
            zma = automol.geom.zmatrix(geo)
            # zma =  cnf_save_fs[-1].file.zmatrix.read(locs)
            # if automol.geom.almost_equal_dist_matrix(inigeo, geo, thresh=.15):
            if automol.zmat.almost_equal(inizma, zma, dist_rtol=0.018, ang_atol=.2):
                cnf_save_path = cnf_save_fs[-1].path(locs)
                ioprinter.info_message('- Similar structure found at {}'.format(cnf_save_path))
                match_dct[ini_locs] = locs
                break

    return match_dct


def unique_fs_confs(cnf_save_fs, cnf_save_locs_lst,
                    ini_cnf_save_fs, ini_cnf_save_locs_lst):
    """ Assess which structures from the cnf_save_fs currently exist
        within the ini_cnf_save_fs. Generate a lst of unique structures
        in the ini_cnf_save_fs.
    """

    uni_ini_cnf_save_locs = []
    for ini_locs in ini_cnf_save_locs_lst:

        # Initialize variable to see if initial struct is found
        found = False

        # Loop over structs in cnf_save, see if they match the current struct
        inigeo =  ini_cnf_save_fs[-1].file.geometry.read(ini_locs)
        inizma = automol.geom.zmatrix(inigeo)
        # inizma =  ini_cnf_save_fs[-1].file.zmatrix.read(ini_locs)
        ini_cnf_save_path = ini_cnf_save_fs[-1].path(ini_locs)
        ioprinter.checking('structures', ini_cnf_save_path)
        for locs in cnf_save_locs_lst:
            geo =  cnf_save_fs[-1].file.geometry.read(locs)
            zma = automol.geom.zmatrix(geo)
            # zma =  cnf_save_fs[-1].file.zmatrix.read(locs)
            if automol.zmat.almost_equal(inizma, zma, dist_rtol=0.018, ang_atol=.2):
                cnf_save_path = cnf_save_fs[-1].path(locs)
                ioprinter.info_message(
                    '- Similar structure found at {}'.format(cnf_save_path))
                found = True
                break

        # If no match was found, add to unique locs lst
        if not found:
            uni_ini_cnf_save_locs.append(ini_locs)

    return uni_ini_cnf_save_locs


def _save_unique_conformer(ret, thy_info, cnf_save_fs, locs,
                           zrxn=None, zma_locs=(0,)):
    """ Save the conformer in the filesystem
    """

    # Set the path to the conformer save filesystem
    cnf_save_path = cnf_save_fs[-1].path(locs)

    # Unpack the ret object and obtain the prog and method
    inf_obj, inp_str, out_str = ret
    prog = inf_obj.prog
    method = inf_obj.method

    # Read the energy and geom from the output
    ene = elstruct.reader.energy(prog, method, out_str)
    geo = elstruct.reader.opt_geometry(prog, out_str)
    zma = elstruct.reader.opt_zmatrix(prog, out_str)
    if zma is None:
        zma = automol.geom.zmatrix(geo)

    # Build the conformer filesystem and save the structural info
    ioprinter.save_conformer(cnf_save_path)
    cnf_save_fs[-1].create(locs)
    cnf_save_fs[-1].file.geometry_info.write(inf_obj, locs)
    cnf_save_fs[-1].file.geometry_input.write(inp_str, locs)
    cnf_save_fs[-1].file.energy.write(ene, locs)
    cnf_save_fs[-1].file.geometry.write(geo, locs)

    # Build the zma filesystem and save the z-matrix
    zma_save_fs = autofile.fs.zmatrix(cnf_save_path)
    zma_save_fs[-1].create(zma_locs)
    zma_save_fs[-1].file.geometry_info.write(inf_obj, zma_locs)
    zma_save_fs[-1].file.geometry_input.write(inp_str, zma_locs)
    zma_save_fs[-1].file.zmatrix.write(zma, zma_locs)

    # Get the tors names
    rotors = automol.rotor.from_zmatrix(zma)
    if any(rotors):
        zma_save_fs[-1].file.torsions.write(rotors, zma_locs)

    # Save the tra and gra for a zrxn
    if zrxn:
        zma_save_fs[-1].file.reaction.write(zrxn, zma_locs)

    # Saving the energy to a SP filesystem
    sp_save_fs = autofile.fs.single_point(cnf_save_path)
    sp_save_fs[-1].create(thy_info[1:4])
    ioprinter.save_conformer_energy(sp_save_fs[-1].root.path())
    sp_save_fs[-1].file.input.write(inp_str, thy_info[1:4])
    sp_save_fs[-1].file.info.write(inf_obj, thy_info[1:4])
    sp_save_fs[-1].file.energy.write(ene, thy_info[1:4])


def _save_sym_indistinct_conformer(geo, cnf_save_fs,
                                   cnf_tosave_locs, cnf_saved_locs):
    """ Save a structure into the SYM directory of a conformer
    """

    # Set the path to the conf filesys with sym similar
    cnf_save_path = cnf_save_fs[-1].path(cnf_saved_locs)

    # Build the sym file sys
    sym_save_fs = autofile.fs.symmetry(cnf_save_path)
    sym_save_path = cnf_save_fs[-1].path(cnf_saved_locs)
    ioprinter.save_symmetry(sym_save_path)
    sym_save_fs[-1].create(cnf_tosave_locs)
    sym_save_fs[-1].file.geometry.write(geo, cnf_tosave_locs)


def _saved_cnf_info(cnf_save_fs, mod_thy_info):
    """ get the locs, geos and enes for saved conformers
    """

    saved_locs = list(cnf_save_fs[-1].existing())
    saved_geos = [cnf_save_fs[-1].file.geometry.read(locs)
                  for locs in saved_locs]
    saved_enes = []
    for locs in saved_locs:
        path = cnf_save_fs[-1].path(locs)
        sp_save_fs = autofile.fs.single_point(path)
        saved_enes.append(sp_save_fs[-1].file.energy.read(
            mod_thy_info[1:4]))

    return saved_locs, saved_geos, saved_enes
