#!/usr/bin/env python3
# -*- python -*-

"""
Waf build script for WCWC documentation.

This script builds HTML documentation from Org-mode files using Emacs.
"""

import os
from waflib import Task, TaskGen, Logs, Utils

APPNAME = 'wcwc-docs'
VERSION = '0.0.2'

top = '.'
out = 'build'


def options(opt):
    """Define command-line options."""
    opt.load("org", tooldir="waft")

def configure(conf):
    """Configure the build environment."""
    conf.load("org", tooldir="waft")

def build(bld):
    """Define build rules."""

    bld.load("org", tooldir="waft")
    orgs = bld.path.ant_glob("docs/wcwc*.org", excl="wcwc-setup.org")
    print(f'{orgs=}')
    print(f'Installing docs to {bld.env.DOCS_PREFIX}')
    bld.build_org_docs(orgs)


