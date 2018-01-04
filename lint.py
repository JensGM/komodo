#!/usr/bin/env python
from __future__ import print_function
import argparse
import distutils.version
from pkg_resources import parse_version
import logging
import yaml as yml

from collections import namedtuple

kerr = namedtuple('KomodoError',
                  ['pkg', 'version', 'maintainer', 'depends', 'err'])

MISSING_PACKAGE = 'missing package'
MISSING_VERSION = 'missing version'
MISSING_DEPENDENCY = 'missing dependency'
MISSING_MAINTAINER = 'missing maintainer'
MALFORMED_VERSION = 'malformed version'
FLOAT_VERSION = 'dangerous version (float interpretable)'


def _kerr(pkg=None, version=None, maintainer=None, depends=None, err=None):
    return kerr(
        pkg=pkg,
        version=version,
        maintainer=maintainer,
        depends=depends,
        err=err)


def _validate(pkg, ver, repo):
    if pkg not in repo:
        return _kerr(pkg=pkg, err=MISSING_PACKAGE)
    if ver not in repo[pkg]:
        return _kerr(pkg=pkg, version=ver, err=MISSING_VERSION)
    if 'maintainer' not in repo[pkg][ver]:
        return _kerr(pkg=pkg, version=ver, err=MISSING_MAINTAINER)
    return _kerr(pkg=pkg, version=ver, maintainer=repo[pkg][ver]['maintainer'])


def lint_maintainers(pkgs, repo):
    return [_validate(pkg, ver, repo) for pkg, ver in pkgs.items()]


def lint_version_numbers(pkgs, repo):
    errs = []
    for pkg, ver in pkgs.items():
        pv = repo[pkg][ver]
        maintainer = pv.get('maintainer', MISSING_MAINTAINER)
        if isinstance(ver, float):
            errs.append(
                _kerr(
                    pkg=pkg,
                    version=ver,
                    maintainer=maintainer,
                    err=FLOAT_VERSION))
        try:
            v = parse_version(ver)
            logging.info('Using %s %s' % (pkg, v))
            if ver.startswith('v') and len(ver) > 1 and '0' <= ver[1] <= '9':
                v = distutils.version.StrictVersion(ver[1:])
            else:
                v = distutils.version.StrictVersion(ver)
        except:
            errs.append(
                _kerr(
                    pkg=pkg,
                    version=ver,
                    maintainer=maintainer,
                    err=MALFORMED_VERSION))
    return errs


def lint_dependencies(pkgs, repo):
    errs = []
    for pkg, ver in pkgs.items():
        pv = repo[pkg][ver]
        maintainer = pv.get('maintainer', MISSING_MAINTAINER)
        if 'depends' not in pv:
            continue
        missing = [d for d in pv['depends'] if d not in pkgs]
        if missing:
            errs.append(
                _kerr(
                    pkg=pkg,
                    version=ver,
                    maintainer=maintainer,
                    depends=missing,
                    err=MISSING_DEPENDENCY))
    return errs


def lint(pkgfile, repofile):
    with open(pkgfile) as p, open(repofile) as r:
        pkgs, repo = yml.load(p), yml.load(r)

    mns = lint_maintainers(pkgs, repo)
    deps = lint_dependencies(pkgs, repo)
    vers = lint_version_numbers(pkgs, repo)
    return mns, deps, vers


def get_args():
    parser = argparse.ArgumentParser(description='lint komodo setup')
    parser.add_argument('pkgfile', type=str)
    parser.add_argument('repofile', type=str)
    parser.add_argument(
        '--verbose',
        help="Massive amount of outputs",
        action="store_const",
        dest="loglevel",
        const=logging.INFO)
    args = parser.parse_args()
    return args


if __name__ == '__main__':
    args = get_args()
    logging.basicConfig(format='%(message)s', level=args.loglevel)

    mns, deps, vers = lint(args.pkgfile, args.repofile)
    print('%d packages' % len(mns))
    if not any([err.err for err in mns + deps + vers]):
        print('No errors found')
        exit(0)

    for err in mns + deps + vers:
        if err.err:
            ver = err.version if err.version else ''
            dep = ': %s' % ', '.join(err.depends) if err.depends else ''
            print('%s for %s %s%s' % (err.err, err.pkg, ver, dep))
    exit('Error in komodo configuration.')
