""" driver for rate constant evaluations
"""

import autorun
import ratefit
from mechroutines.pf import ktp as ktproutines
from mechlib.amech_io import writer
from mechlib.amech_io import parser
from mechlib.amech_io import job_path
from mechlib.amech_io import output_path
from mechlib.amech_io import printer as ioprinter
from mechlib.reaction import split_unstable


def run(pes_inf,
        ktp_tsk_lst,
        spc_dct, thy_dct, rxn_lst,
        pes_model_dct, spc_model_dct,
        run_inp_dct):
    """ main driver for generation of full set of rate constants on a single PES
    """

    # ---------------------------------------------- #
    # PREPARE INFORMATION TO PASS TO KTPDRIVER TASKS #
    # ---------------------------------------------- #

    # Unpack the ktp tsks lst
    _ = ''

    # Print PESs that are being run
    if pes_inf is not None:
        pes_formula, pes_idx, sub_pes_idx = pes_inf
        ioprinter.pes(pes_idx, pes_formula, sub_pes_idx)
        for rxn in rxn_lst:
            ioprinter.channel(rxn['chn_idx'], rxn['reacs'], rxn['prods'])

    # Pull globally useful information from the dictionaries
    run_prefix = run_inp_dct['run_prefix']
    save_prefix = run_inp_dct['save_prefix']

    # Obtain all of the transitions states
    ioprinter.message('Identifying reaction classes for transition states...')
    spc_dct = parser.species.build_sadpt_dct2(
        pes_idx, rxn_lst, ktp_tsk_lst,
        spc_model_dct, thy_dct,
        run_inp_dct, spc_dct, run_prefix, save_prefix)

    # Set reaction list with unstable species broken apart
    ioprinter.message('Identifying stability of all species...', newline=1)
    rxn_lst = split_unstable(
        rxn_lst, spc_dct, spc_model_dct, thy_dct, save_prefix)

    # Build the MESS label idx dictionary for the PES
    label_dct = ktproutines.label.make_pes_label_dct(
        rxn_lst, pes_idx, spc_dct, spc_model_dct)

    # Set paths where files will be written and read
    mess_path = job_path(
        run_prefix, 'MESS', 'RATE', pes_formula, locs_idx=sub_pes_idx)

    # --------------------------------- #
    # RUN THE REQUESTED KTPDRIVER TASKS #
    # --------------------------------- #

    # Write the MESS file
    write_messrate_tsk = parser.tsks.extract_tsk('write_messrate', ktp_tsk_lst)
    if write_messrate_tsk is not None:

        tsk_key_dct = write_messrate_tsk[3]  # check format of the ktp tsk lst
        pes_model = tsk_key_dct['pes_model']

        ioprinter.messpf('write_header')

        # Write the strings for the MESS input file
        globkey_str = ktproutines.rates.make_header_str(
            spc_dct,
            temps=pes_model_dct[pes_model]['rate_temps'],
            pressures=pes_model_dct[pes_model]['pressures'])

        # Write the energy transfer section strings for MESS file
        etransfer = pes_model_dct[pes_model]['etransfer']
        energy_trans_str = ktproutines.rates.make_global_etrans_str(
            rxn_lst, spc_dct, etransfer)

        # Write the MESS strings for all the PES channels
        chan_str, dats, _, _ = ktproutines.rates.make_pes_mess_str(
            spc_dct, rxn_lst, pes_idx,
            run_prefix, save_prefix, label_dct,
            spc_model_dct, thy_dct)

        # Combine strings together
        mess_inp_str = ktproutines.rates.make_messrate_str(
            globkey_str, energy_trans_str, chan_str)

        # Write the MESS file into the filesystem
        ioprinter.obj('line_plus')
        ioprinter.writing('MESS input file', mess_path)
        ioprinter.debug_message(mess_inp_str)

        autorun.write_input(
            mess_path, mess_inp_str,
            aux_dct=dats, input_name='mess.inp')

    # Run mess to produce rates (currently nothing from tsk lst keys used)
    run_messrate_tsk = parser.tsks.extract_tsk('run_messrate', ktp_tsk_lst)
    if run_messrate_tsk is not None:

        ioprinter.obj('vspace')
        ioprinter.obj('line_dash')
        ioprinter.running('MESS for the input file', mess_path)
        autorun.run_script(autorun.SCRIPT_DCT['messrate'], mess_path)

    # Fit rate output to modified Arrhenius forms, print in ChemKin format
    run_fit_tsk = parser.tsks.extract_tsk('run_fit', ktp_tsk_lst)
    if run_fit_tsk is not None:

        tsk_key_dct = write_messrate_tsk[3]  # check format of the ktp tsk lst
        pes_model = tsk_key_dct['pes_model']

        ioprinter.obj('vspace')
        ioprinter.obj('line_dash')
        ioprinter.info_message(
            'Fitting Rate Constants for PES to Functional Forms', newline=1)

        ckin_str = ratefit.fit.fit_ktp_dct(
            mess_path=mess_path,
            inp_fit_method=pes_model_dct[pes_model]['fit_method'],
            pdep_fit=pes_model_dct[pes_model]['pdep_fit'],
            arrfit_fit=pes_model_dct[pes_model]['arrfit_fit'],
            chebfit_fit=pes_model_dct[pes_model]['chebfit_fit'],
            troefit_fit=pes_model_dct[pes_model]['troefit_fit'],
            label_dct=label_dct,
            fit_temps=pes_model_dct[pes_model]['rate_temps'],
            fit_pressures=pes_model_dct[pes_model]['pressures'],
            fit_tunit=pes_model_dct[pes_model]['tunit'],
            fit_punit=pes_model_dct[pes_model]['punit']
        )

        ckin_path = output_path('CKIN')
        writer.ckin.write_rxn_file(
            {pes_formula: ckin_str}, pes_formula, ckin_path)
