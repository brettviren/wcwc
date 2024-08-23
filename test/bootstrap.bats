#!/usr/bin/env bats

bats_require_minimum_version 1.5.0

# Test bootstrapping a green field.

export WCWC_BUILDER_IMAGE=wcwc-test-bootstrap
export TMPDIR=$HOME/.cache/wcwc/testing
export WCWC_PREFIX=$TMPDIR/wcwc

wcwc () {
    local lvl=info
    command wcwc -L $lvl "$@"
}

setup_file () {
    mkdir -p $WCWC_PREFIX/.spack || true

    podman --version            # make sure exists
    wcwc admin builder # --force
}

@test "wcwc exists with version" {
    run -0 wcwc version
    [[ -n "$output" ]]
}

@test "init spack" {
    # must use develop until 0.23 is released for {namespace} support
    run -0 wcwc admin init --tag develop spack
    [[ -f $WCWC_PREFIX/spack/bin/spack ]]
    [[ -d $WCWC_PREFIX/.spack/bootstrap ]]
}

@test "install zlib" {
    run -0 wcwc admin install zlib
    [[ -n "$(wcwc find zlib | grep ^zlib)" ]]
}

@test "make a system environment" {
    run -0 wcwc admin env -e test-system-env --target spack zlib
    local edir=$WCWC_PREFIX/stacks/spack/environments/test-system-env
    [[ -d "$edir" ]]
    run grep -q '\bzlib\b' "$edir/spack.yaml"
    test -L $edir/.spack-env/._view/*/lib/libz.so
}

@test "use a system environment" {
    run -0 wcwc admin shell -e test-system-env -c 'spack find zlib'
}

teardown_file () {
    # podman image rm $WCWC_BUILDER_IMAGE
    echo "not removing podman image \"$WCWC_BUILDER_IMAGE\" in order to speed up test rerunning" 1>&3
}


