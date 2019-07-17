""" test autofile.system
"""
import os
import tempfile
import numpy
import pytest
import automol
import autofile.info
import autofile.system

PREFIX = tempfile.mkdtemp()
print(PREFIX)

# create a dummy root DataSeriesDir for testing
ROOT_SPEC_DFILE = autofile.system.file_.locator(
    file_prefix='dir',
    map_dct_={
        'loc1': lambda locs: locs[0],
        'loc2': lambda locs: locs[1],
        'other': lambda locs: 'something else',
    },
    loc_keys=['loc1', 'loc2'],
)
ROOT_DSDIR = autofile.system.model.DataSeriesDir(
    map_=lambda x: os.path.join(*map(str, x)),
    nlocs=2,
    depth=2,
    loc_dfile=ROOT_SPEC_DFILE,
)


def test__file__input_file():
    """ test autofile.system.file_.input_file
    """
    ref_inp_str = '<input file contents>'

    dfm = autofile.system.data_file_manager()

    assert not dfm.geometry_input.exists(PREFIX)
    dfm.geometry_input.write(ref_inp_str, PREFIX)
    assert dfm.geometry_input.exists(PREFIX)

    inp_str = dfm.geometry_input.read(PREFIX)
    assert inp_str == ref_inp_str
    print(inp_str)


def test__file__information():
    """ test autofile.system.file_.information
    """
    ref_inf_obj = autofile.system.info.run(
        job='optimization',
        prog='psi4',
        method='b3lyp',
        basis='6-31g*',
        status='running',
    )

    dfm = autofile.system.data_file_manager()

    assert not dfm.geometry_info.exists(PREFIX)
    dfm.geometry_info.write(ref_inf_obj, PREFIX)
    assert dfm.geometry_info.exists(PREFIX)

    inf_obj = dfm.geometry_info.read(PREFIX)
    assert inf_obj == ref_inf_obj
    print(inf_obj)


def test__file__energy():
    """ test autofile.system.file_.energy
    """
    ref_ene = -187.38518070487598

    dfm = autofile.system.data_file_manager()

    assert not dfm.geometry_energy.exists(PREFIX)
    dfm.geometry_energy.write(ref_ene, PREFIX)
    assert dfm.geometry_energy.exists(PREFIX)

    ene = dfm.geometry_energy.read(PREFIX)
    assert ene == ref_ene
    print(ene)


def test__file__geometry():
    """ test autofile.system.file_.geometry
    """
    ref_geo = (('C', (0.066541036329, -0.86543409422, -0.56994517889)),
               ('O', (0.066541036329, -0.86543409422, 2.13152981129)),
               ('O', (0.066541036329, 1.6165813318, -1.63686376233)),
               ('H', (-1.52331011945, -1.99731957213, -1.31521725797)),
               ('H', (1.84099386813, -1.76479255185, -1.16213243427)),
               ('H', (-1.61114836922, -0.17751142359, 2.6046492029)),
               ('H', (-1.61092727126, 2.32295906780, -1.19178601663)))

    dfm = autofile.system.data_file_manager()

    assert not dfm.geometry.exists(PREFIX)
    dfm.geometry.write(ref_geo, PREFIX)
    assert dfm.geometry.exists(PREFIX)

    geo = dfm.geometry.read(PREFIX)
    assert automol.geom.almost_equal(geo, ref_geo)
    print(geo)


def test__file__gradient():
    """ test autofile.system.file_.gradient
    """
    ref_grad = ((0.00004103632, 0.00003409422, 0.00004517889),
                (0.00004103632, 0.00003409422, 0.00002981129),
                (0.00004103632, 0.00008133180, 0.00006376233),
                (0.00001011945, 0.00001957213, 0.00001725797),
                (0.00009386813, 0.00009255185, 0.00003243427),
                (0.00004836922, 0.00001142359, 0.00004920290),
                (0.00002727126, 0.00005906780, 0.00008601663))

    dfm = autofile.system.data_file_manager()

    assert not dfm.gradient.exists(PREFIX)
    dfm.gradient.write(ref_grad, PREFIX)
    assert dfm.gradient.exists(PREFIX)

    grad = dfm.gradient.read(PREFIX)
    assert numpy.allclose(grad, ref_grad)
    print(grad)


def test__file__hessian():
    """ test autofile.system.file_.hessian
    """
    ref_hess = (
        (-0.21406, 0., 0., -0.06169, 0., 0., 0.27574, 0., 0.),
        (0., 2.05336, 0.12105, 0., -0.09598, 0.08316, 0., -1.95737, -0.20421),
        (0., 0.12105, 0.19177, 0., -0.05579, -0.38831, 0., -0.06525, 0.19654),
        (-0.06169, 0., 0., 0.0316, 0., 0., 0.03009, 0., 0.),
        (0., -0.09598, -0.05579, 0., 0.12501, -0.06487, 0., -0.02902,
         0.12066),
        (0., 0.08316, -0.38831, 0., -0.06487, 0.44623, 0., -0.01829,
         -0.05792),
        (0.27574, 0., 0., 0.03009, 0., 0., -0.30583, 0., 0.),
        (0., -1.95737, -0.06525, 0., -0.02902, -0.01829, 0., 1.9864,
         0.08354),
        (0., -0.20421, 0.19654, 0., 0.12066, -0.05792, 0., 0.08354,
         -0.13862))

    dfm = autofile.system.data_file_manager()

    assert not dfm.hessian.exists(PREFIX)
    dfm.hessian.write(ref_hess, PREFIX)
    assert dfm.hessian.exists(PREFIX)

    hess = dfm.hessian.read(PREFIX)
    assert numpy.allclose(hess, ref_hess)
    print(hess)


def test__file__zmatrix():
    """ test autofile.system.file_.zmatrix
    """
    ref_zma = (
        (('C', (None, None, None), (None, None, None)),
         ('O', (0, None, None), ('r1', None, None)),
         ('O', (0, 1, None), ('r2', 'a1', None)),
         ('H', (0, 1, 2), ('r3', 'a2', 'd1')),
         ('H', (0, 1, 2), ('r4', 'a3', 'd2')),
         ('H', (1, 0, 2), ('r5', 'a4', 'd3')),
         ('H', (2, 0, 1), ('r6', 'a5', 'd4'))),
        {'r1': 2.65933,
         'r2': 2.65933, 'a1': 1.90743,
         'r3': 2.06844, 'a2': 1.93366, 'd1': 4.1477,
         'r4': 2.06548, 'a3': 1.89469, 'd2': 2.06369,
         'r5': 1.83126, 'a4': 1.86751, 'd3': 1.44253,
         'r6': 1.83126, 'a5': 1.86751, 'd4': 4.84065})

    dfm = autofile.system.data_file_manager()

    assert not dfm.zmatrix.exists(PREFIX)
    dfm.zmatrix.write(ref_zma, PREFIX)
    assert dfm.zmatrix.exists(PREFIX)

    zma = dfm.zmatrix.read(PREFIX)
    assert automol.zmatrix.almost_equal(zma, ref_zma)
    print(zma)


def test__file__vmatrix():
    """ test autofile.system.file_.vmatrix
    """
    ref_vma = (('C', (None, None, None), (None, None, None)),
               ('O', (0, None, None), ('r1', None, None)),
               ('O', (0, 1, None), ('r2', 'a1', None)),
               ('H', (0, 1, 2), ('r3', 'a2', 'd1')),
               ('H', (0, 1, 2), ('r4', 'a3', 'd2')),
               ('H', (1, 0, 2), ('r5', 'a4', 'd3')),
               ('H', (2, 0, 1), ('r6', 'a5', 'd4')))

    dfm = autofile.system.data_file_manager()

    assert not dfm.vmatrix.exists(PREFIX)
    dfm.vmatrix.write(ref_vma, PREFIX)
    assert dfm.vmatrix.exists(PREFIX)

    vma = dfm.vmatrix.read(PREFIX)
    assert vma == ref_vma
    print(vma)


def test__file__trajectory():
    """ test autofile.system.file_.trajectory
    """
    ref_geos = [
        (('C', (0.0, 0.0, 0.0)),
         ('O', (0.0, 0.0, 2.699694868173)),
         ('O', (0.0, 2.503038629201, -1.011409768236)),
         ('H', (-1.683942509299, -1.076047850358, -0.583313101501)),
         ('H', (1.684063451772, -0.943916309940, -0.779079279468)),
         ('H', (1.56980872050, 0.913848877557, 3.152002706027)),
         ('H', (-1.57051358834, 3.264399836517, -0.334901043405))),
        (('C', (0.0, 0.0, 0.0)),
         ('O', (0.0, 0.0, 2.70915105770)),
         ('O', (0.0, 2.55808068205, -0.83913477573)),
         ('H', (-1.660164085463, -1.04177010816, -0.73213470306)),
         ('H', (1.711679909369, -0.895873802652, -0.779058492481)),
         ('H', (0.0238181080852, -1.813377410537, 3.16912929390)),
         ('H', (-1.36240560905, 3.348313125118, 0.1732746576216)))]
    ref_comments = ['energy: -187.3894105487809',
                    'energy: -187.3850624381528']

    ref_traj = list(zip(ref_comments, ref_geos))

    dfm = autofile.system.data_file_manager()

    assert not dfm.trajectory.exists(PREFIX)
    dfm.trajectory.write(ref_traj, PREFIX)
    assert dfm.trajectory.exists(PREFIX)

    # I'm not going to bother implementing a reader, since the trajectory files
    # are for human use only -- we aren't going to use this for data storage


def test__file__lennard_jones_epsilon():
    """ test autofile.system.file_.lennard_jones_epsilon
    """
    ref_eps = 247.880866746988

    eps_dfile = autofile.system.file_.lennard_jones_epsilon('test')

    assert not eps_dfile.exists(PREFIX)
    eps_dfile.write(ref_eps, PREFIX)
    assert eps_dfile.exists(PREFIX)

    eps = eps_dfile.read(PREFIX)
    assert numpy.isclose(eps, ref_eps)
    print(eps)


def test__file__lennard_jones_sigma():
    """ test autofile.system.file_.lennard_jones_sigma
    """
    ref_sig = 3.55018590361446

    sig_dfile = autofile.system.file_.lennard_jones_sigma('test')

    assert not sig_dfile.exists(PREFIX)
    sig_dfile.write(ref_sig, PREFIX)
    assert sig_dfile.exists(PREFIX)

    sig = sig_dfile.read(PREFIX)
    assert numpy.isclose(sig, ref_sig)
    print(sig)


def test__dir__run_trunk():
    """ test dir_.run_trunk
    """
    prefix = os.path.join(PREFIX, 'run_trunk')
    os.mkdir(prefix)

    dsdir = autofile.system.dir_.run_trunk(ROOT_DSDIR)

    root_locs_lst = [
        [1, 'a'],
        [1, 'b'],
        [2, 'a'],
        [2, 'b'],
        [2, 'c'],
    ]

    for root_locs in root_locs_lst:
        locs = root_locs

        assert not dsdir.exists(prefix, locs)
        dsdir.create(prefix, locs)
        assert dsdir.exists(prefix, locs)

    assert sorted(ROOT_DSDIR.existing(prefix)) == sorted(root_locs_lst)


def test__dir__run_leaf():
    """ test dir_.run_leaf
    """
    prefix = os.path.join(PREFIX, 'run_leaf')
    os.mkdir(prefix)

    dsdir = autofile.system.dir_.run_leaf(ROOT_DSDIR)

    root_locs_lst = [
        [1, 'a'],
        [1, 'b'],
        [2, 'a'],
        [2, 'b'],
        [2, 'c'],
    ]
    leaf_locs_lst = [
        ['energy'],
        ['gradient'],
        ['hessian'],
        ['optimization'],
    ]

    for root_locs in root_locs_lst:
        for leaf_locs in leaf_locs_lst:
            locs = root_locs + leaf_locs

            assert not dsdir.exists(prefix, locs)
            dsdir.create(prefix, locs)
            assert dsdir.exists(prefix, locs)

    assert sorted(ROOT_DSDIR.existing(prefix)) == sorted(root_locs_lst)

    print(dsdir.existing(prefix, root_locs_lst[-1]))
    for root_locs in root_locs_lst:
        assert (sorted(dsdir.existing(prefix, root_locs)) ==
                sorted(leaf_locs_lst))


def test__dir__subrun_leaf():
    """ test dir_.subrun_leaf
    """
    prefix = os.path.join(PREFIX, 'subrun_leaf')
    os.mkdir(prefix)

    dsdir = autofile.system.dir_.subrun_leaf(ROOT_DSDIR)

    root_locs_lst = [
        [1, 'a'],
        [1, 'b'],
        [2, 'a'],
        [2, 'b'],
        [2, 'c'],
    ]
    leaf_locs_lst = [
        [0, 0],
        [0, 1],
        [0, 2],
        [1, 0],
        [1, 1],
        [2, 0],
    ]

    for root_locs in root_locs_lst:
        for leaf_locs in leaf_locs_lst:
            locs = root_locs + leaf_locs

            assert not dsdir.exists(prefix, locs)
            dsdir.create(prefix, locs)
            assert dsdir.exists(prefix, locs)

    assert sorted(ROOT_DSDIR.existing(prefix)) == sorted(root_locs_lst)

    print(dsdir.existing(prefix, root_locs_lst[-1]))
    for root_locs in root_locs_lst:
        assert (sorted(dsdir.existing(prefix, root_locs)) ==
                sorted(leaf_locs_lst))


def test__dir__species_trunk():
    """ test dir_.species_trunk
    """
    prefix = os.path.join(PREFIX, 'species_trunk')
    os.mkdir(prefix)

    # without a root directory
    dsdir = autofile.system.dir_.species_trunk()

    assert not dsdir.exists(prefix)
    dsdir.create(prefix)
    assert dsdir.exists(prefix)

    # with a root directory
    dsdir = autofile.system.dir_.species_trunk(ROOT_DSDIR)

    root_locs_lst = [
        [1, 'a'],
        [1, 'b'],
        [2, 'a'],
        [2, 'b'],
        [2, 'c'],
    ]

    for root_locs in root_locs_lst:
        locs = root_locs

        assert not dsdir.exists(prefix, locs)
        dsdir.create(prefix, locs)
        assert dsdir.exists(prefix, locs)

    assert sorted(ROOT_DSDIR.existing(prefix)) == sorted(root_locs_lst)


def test__dir__species_leaf():
    """ test dir_.species_leaf
    """
    prefix = os.path.join(PREFIX, 'species_leaf')
    os.mkdir(prefix)

    dsdir = autofile.system.dir_.species_leaf(ROOT_DSDIR)

    root_locs_lst = [
        [1, 'a'],
        [1, 'b'],
        [2, 'a'],
        [2, 'b'],
        [2, 'c'],
    ]
    branch_locs_lst = [
        ['InChI=1S/C2H2F2/c3-1-2-4/h1-2H/b2-1+', 0, 1],
        ['InChI=1S/C2H2F2/c3-1-2-4/h1-2H/b2-1-', 0, 1],
        ['InChI=1S/C5H5O/c1-2-3-4-5-6/h1-5H/b4-3-', 0, 2],
        ['InChI=1S/O', 0, 1],
        ['InChI=1S/O', 0, 3],
    ]

    for root_locs in root_locs_lst:
        for branch_locs in branch_locs_lst:
            locs = root_locs + branch_locs

            assert not dsdir.exists(prefix, locs)
            dsdir.create(prefix, locs)
            assert dsdir.exists(prefix, locs)

    assert sorted(ROOT_DSDIR.existing(prefix)) == sorted(root_locs_lst)

    print(dsdir.existing(prefix, root_locs_lst[-1]))
    for root_locs in root_locs_lst:
        assert (sorted(dsdir.existing(prefix, root_locs)) ==
                sorted(branch_locs_lst))


def test__dir__reaction_trunk():
    """ test dir_.reaction_trunk
    """
    prefix = os.path.join(PREFIX, 'reaction_trunk')
    os.mkdir(prefix)

    # without a root directory
    dsdir = autofile.system.dir_.reaction_trunk()

    assert not dsdir.exists(prefix)
    dsdir.create(prefix)
    assert dsdir.exists(prefix)

    # with a root directory
    dsdir = autofile.system.dir_.reaction_trunk(ROOT_DSDIR)

    root_locs_lst = [
        [1, 'a'],
        [1, 'b'],
        [2, 'a'],
        [2, 'b'],
        [2, 'c'],
    ]

    for root_locs in root_locs_lst:
        locs = root_locs

        assert not dsdir.exists(prefix, locs)
        dsdir.create(prefix, locs)
        assert dsdir.exists(prefix, locs)

    assert sorted(ROOT_DSDIR.existing(prefix)) == sorted(root_locs_lst)


def test__dir__reaction_leaf():
    """ test dir_.reaction_leaf
    """
    prefix = os.path.join(PREFIX, 'reaction_leaf')
    os.mkdir(prefix)

    dsdir = autofile.system.dir_.reaction_leaf(ROOT_DSDIR)

    root_locs_lst = [
        [1, 'a'],
        [1, 'b'],
        [2, 'a'],
        [2, 'b'],
        [2, 'c'],
    ]

    branch_locs_lst = [
        [
            [['InChI=1S/C2H5O2/c1-2-4-3/h3H,1-2H2'],
             ['InChI=1S/C2H4/c1-2/h1-2H2', 'InChI=1S/HO2/c1-2/h1H']],
            [[0], [0, 0]],
            [[2], [1, 2]],
            2,
        ],
        [
            [['InChI=1S/CH3/h1H3', 'InChI=1S/HO/h1H'],
             ['InChI=1S/CH2/h1H2', 'InChI=1S/H2O/h1H2']],
            [[0, 0], [0, 0]],
            [[2, 2], [1, 1]],
            1,
        ],
        [
            [['InChI=1S/CH3O3/c2-1-4-3/h3H,1H2'],
             ['InChI=1S/CH3O3/c2-1-4-3/h2H,1H2']],
            [[0], [0]],
            [[2], [2]],
            2,
        ],
    ]

    for root_locs in root_locs_lst:
        for branch_locs in branch_locs_lst:
            locs = root_locs + branch_locs

            assert not dsdir.exists(prefix, locs)
            dsdir.create(prefix, locs)
            assert dsdir.exists(prefix, locs)

    assert sorted(ROOT_DSDIR.existing(prefix)) == sorted(root_locs_lst)

    print(dsdir.existing(prefix, root_locs_lst[-1]))
    for root_locs in root_locs_lst:
        assert (sorted(dsdir.existing(prefix, root_locs)) ==
                sorted(branch_locs_lst))


def test__dir__theory_leaf():
    """ test dir_.theory_leaf
    """
    prefix = os.path.join(PREFIX, 'theory_leaf')
    os.mkdir(prefix)

    dsdir = autofile.system.dir_.theory_leaf(ROOT_DSDIR)

    root_locs_lst = [
        [1, 'a'],
        [1, 'b'],
        [2, 'a'],
        [2, 'b'],
        [2, 'c'],
    ]
    branch_locs_lst = [
        ['hf', 'sto-3g', True],
        ['hf', 'sto-3g', False],
        ['b3lyp', 'sto-3g', False],
        ['b3lyp', '6-31g*', False],
    ]

    for root_locs in root_locs_lst:
        for branch_locs in branch_locs_lst:
            locs = root_locs + branch_locs

            assert not dsdir.exists(prefix, locs)
            dsdir.create(prefix, locs)
            assert dsdir.exists(prefix, locs)

    assert sorted(ROOT_DSDIR.existing(prefix)) == sorted(root_locs_lst)

    print(dsdir.existing(prefix, root_locs_lst[-1]))
    for root_locs in root_locs_lst:
        assert (sorted(dsdir.existing(prefix, root_locs)) ==
                sorted(branch_locs_lst))


def test__dir__conformer_trunk():
    """ test dir_.conformer_trunk
    """
    prefix = os.path.join(PREFIX, 'conformer_trunk')
    os.mkdir(prefix)

    # without a root directory
    dsdir = autofile.system.dir_.conformer_trunk()

    assert not dsdir.exists(prefix)
    dsdir.create(prefix)
    assert dsdir.exists(prefix)

    # with a root directory
    dsdir = autofile.system.dir_.conformer_trunk(ROOT_DSDIR)

    root_locs_lst = [
        [1, 'a'],
        [1, 'b'],
        [2, 'a'],
        [2, 'b'],
        [2, 'c'],
    ]

    for root_locs in root_locs_lst:
        locs = root_locs

        assert not dsdir.exists(prefix, locs)
        dsdir.create(prefix, locs)
        assert dsdir.exists(prefix, locs)

    assert sorted(ROOT_DSDIR.existing(prefix)) == sorted(root_locs_lst)


def test__dir__conformer_leaf():
    """ test dir_.conformer_leaf
    """
    prefix = os.path.join(PREFIX, 'conformer_leaf')
    os.mkdir(prefix)

    dsdir = autofile.system.dir_.conformer_leaf(ROOT_DSDIR)

    root_locs_lst = [
        [1, 'a'],
        [1, 'b'],
        [2, 'a'],
        [2, 'b'],
        [2, 'c'],
    ]

    nconfs = 10
    branch_locs_lst = [
        [autofile.system.generate_new_conformer_id()] for _ in range(nconfs)]

    for root_locs in root_locs_lst:
        for branch_locs in branch_locs_lst:
            locs = root_locs + branch_locs

            assert not dsdir.exists(prefix, locs)
            dsdir.create(prefix, locs)
            assert dsdir.exists(prefix, locs)

    assert sorted(ROOT_DSDIR.existing(prefix)) == sorted(root_locs_lst)

    print(dsdir.existing(prefix, root_locs_lst[-1]))
    for root_locs in root_locs_lst:
        assert (sorted(dsdir.existing(prefix, root_locs)) ==
                sorted(branch_locs_lst))


def test__dir__single_point_trunk():
    """ test dir_.single_point_trunk
    """
    prefix = os.path.join(PREFIX, 'single_point_trunk')
    os.mkdir(prefix)

    dsdir = autofile.system.dir_.single_point_trunk(ROOT_DSDIR)

    root_locs_lst = [
        [1, 'a'],
        [1, 'b'],
        [2, 'a'],
        [2, 'b'],
        [2, 'c'],
    ]

    for root_locs in root_locs_lst:
        locs = root_locs

        assert not dsdir.exists(prefix, locs)
        dsdir.create(prefix, locs)
        assert dsdir.exists(prefix, locs)

    assert sorted(ROOT_DSDIR.existing(prefix)) == sorted(root_locs_lst)


def test__dir__scan_trunk():
    """ test dir_.scan_trunk
    """
    prefix = os.path.join(PREFIX, 'scan_trunk')
    os.mkdir(prefix)

    # without a root directory
    dsdir = autofile.system.dir_.scan_trunk()

    assert not dsdir.exists(prefix)
    dsdir.create(prefix)
    assert dsdir.exists(prefix)

    # with a root directory
    dsdir = autofile.system.dir_.scan_trunk(ROOT_DSDIR)

    root_locs_lst = [
        [1, 'a'],
        [1, 'b'],
        [2, 'a'],
        [2, 'b'],
        [2, 'c'],
    ]

    for root_locs in root_locs_lst:
        locs = root_locs

        assert not dsdir.exists(prefix, locs)
        dsdir.create(prefix, locs)
        assert dsdir.exists(prefix, locs)

    assert sorted(ROOT_DSDIR.existing(prefix)) == sorted(root_locs_lst)


def test__dir__scan_branch():
    """ test dir_.scan_branch
    """
    prefix = os.path.join(PREFIX, 'scan_branch')
    os.mkdir(prefix)

    dsdir = autofile.system.dir_.scan_branch(ROOT_DSDIR)

    root_locs_lst = [
        [1, 'a'],
        [1, 'b'],
        [2, 'a'],
        [2, 'b'],
        [2, 'c'],
    ]
    branch_locs_lst = [
        [['d3']],
        [['d3', 'd4']],
    ]

    for root_locs in root_locs_lst:
        for branch_locs in branch_locs_lst:
            locs = root_locs + branch_locs

            assert not dsdir.exists(prefix, locs)
            dsdir.create(prefix, locs)
            assert dsdir.exists(prefix, locs)

    assert sorted(ROOT_DSDIR.existing(prefix)) == sorted(root_locs_lst)

    print(dsdir.existing(prefix, root_locs_lst[-1]))
    for root_locs in root_locs_lst:
        assert (sorted(dsdir.existing(prefix, root_locs)) ==
                sorted(branch_locs_lst))


def test__dir__scan_leaf():
    """ test dir_.scan_leaf
    """
    prefix = os.path.join(PREFIX, 'scan_leaf')
    os.mkdir(prefix)

    dsdir = autofile.system.dir_.scan_leaf(ROOT_DSDIR)

    root_locs_lst = [
        [1, 'a'],
        [1, 'b'],
        [2, 'a'],
        [2, 'b'],
        [2, 'c'],
    ]
    leaf_locs_lst = [
        [[0, 0]],
        [[1, 0]],
        [[2, 0]],
        [[0, 1]],
        [[1, 1]],
        [[2, 1]],
        [[0, 2]],
        [[1, 2]],
        [[2, 2]],
        [[0, 3]],
        [[1, 3]],
        [[2, 3]],
        [[0, 4]],
        [[1, 4]],
        [[2, 4]],
    ]

    for root_locs in root_locs_lst:
        for leaf_locs in leaf_locs_lst:
            locs = root_locs + leaf_locs

            assert not dsdir.exists(prefix, locs)
            dsdir.create(prefix, locs)
            assert dsdir.exists(prefix, locs)

    assert sorted(ROOT_DSDIR.existing(prefix)) == sorted(root_locs_lst)

    print(dsdir.existing(prefix, root_locs_lst[-1]))
    for root_locs in root_locs_lst:
        assert (sorted(dsdir.existing(prefix, root_locs)) ==
                sorted(leaf_locs_lst))


def test__dir__tau_trunk():
    """ test dir_.tau_trunk
    """
    prefix = os.path.join(PREFIX, 'tau_trunk')
    os.mkdir(prefix)

    # without a root directory
    dsdir = autofile.system.dir_.tau_trunk()

    assert not dsdir.exists(prefix)
    dsdir.create(prefix)
    assert dsdir.exists(prefix)

    # with a root directory
    dsdir = autofile.system.dir_.tau_trunk(ROOT_DSDIR)

    root_locs_lst = [
        [1, 'a'],
        [1, 'b'],
        [2, 'a'],
        [2, 'b'],
        [2, 'c'],
    ]

    for root_locs in root_locs_lst:
        locs = root_locs

        assert not dsdir.exists(prefix, locs)
        dsdir.create(prefix, locs)
        assert dsdir.exists(prefix, locs)

    assert sorted(ROOT_DSDIR.existing(prefix)) == sorted(root_locs_lst)


def test__dir__tau_leaf():
    """ test dir_.tau_leaf
    """
    prefix = os.path.join(PREFIX, 'tau_leaf')
    os.mkdir(prefix)

    dsdir = autofile.system.dir_.tau_leaf(ROOT_DSDIR)

    root_locs_lst = [
        [1, 'a'],
        [1, 'b'],
        [2, 'a'],
        [2, 'b'],
        [2, 'c'],
    ]

    nconfs = 10
    branch_locs_lst = [
        [autofile.system.generate_new_tau_id()] for _ in range(nconfs)]

    for root_locs in root_locs_lst:
        for branch_locs in branch_locs_lst:
            locs = root_locs + branch_locs

            assert not dsdir.exists(prefix, locs)
            dsdir.create(prefix, locs)
            assert dsdir.exists(prefix, locs)

    assert sorted(ROOT_DSDIR.existing(prefix)) == sorted(root_locs_lst)

    print(dsdir.existing(prefix, root_locs_lst[-1]))
    for root_locs in root_locs_lst:
        assert (sorted(dsdir.existing(prefix, root_locs)) ==
                sorted(branch_locs_lst))

    with pytest.raises(ValueError):
        dsdir.remove(prefix, locs)
    assert dsdir.exists(prefix, locs)


def test__dir__build_trunk():
    """ test dir_.build_trunk
    """
    prefix = os.path.join(PREFIX, 'build_trunk')
    os.mkdir(prefix)

    dsdir = autofile.system.dir_.build_trunk(ROOT_DSDIR)

    root_alocs_lst = [
        [1, 'a'],
        [1, 'b'],
        [2, 'a'],
        [2, 'b'],
        [2, 'c'],
    ]
    rlocs_lst = [
        ['MESS'],
    ]

    for root_alocs in root_alocs_lst:
        for rlocs in rlocs_lst:
            alocs = root_alocs + rlocs

            assert not dsdir.exists(prefix, alocs)
            dsdir.create(prefix, alocs)
            assert dsdir.exists(prefix, alocs)

    assert sorted(ROOT_DSDIR.existing(prefix)) == sorted(root_alocs_lst)

    print(dsdir.existing(prefix, root_alocs_lst[-1]))
    for root_alocs in root_alocs_lst:
        assert (sorted(dsdir.existing(prefix, root_alocs)) ==
                sorted(rlocs_lst))


if __name__ == '__main__':
    test__file__input_file()
    test__file__information()
    # test__file__energy()
    # test__file__geometry()
    # test__file__gradient()
    # test__file__hessian()
    # test__file__zmatrix()
    # test__file__vmatrix()
    # test__file__trajectory()
    # test__file__lennard_jones_epsilon()
    # test__file__lennard_jones_sigma()
    # test__dir__run_trunk()
    # test__dir__run_leaf()
    # test__dir__subrun_leaf()
    # test__dir__species_trunk()
    # test__dir__species_leaf()
    # test__dir__theory_leaf()
    # test__dir__conformer_trunk()
    # test__dir__conformer_leaf()
    # test__dir__single_point_trunk()
    # test__dir__scan_trunk()
    # test__dir__scan_branch()
    # test__dir__scan_leaf()
    # test__dir__tau_trunk()
    # test__dir__tau_leaf()
    # test__dir__reaction_trunk()
    # test__dir__reaction_leaf()
    # test__dir__build_trunk()
    # test__dir__build_leaf()
