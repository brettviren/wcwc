#!/usr/bin/env bats

# Tests outside of podman

bats_require_minimum_version 1.5.0

#export TMPDIR=$HOME/.cache/wcwc/testing/native
export WCWC_PREFIX=$BATS_TMPDIR/wcwc-testing/native
export SPACK_USER_CONFIG_PATH=$WCWC_PREFIX/.spack
export SPACK_DISABLE_LOCAL_CONFIG=true

wcwc () {
    local lvl=info
    command wcwc -L $lvl "$@"
}

setup_file () {
    if [ ! -d $WCWC_PREFIX ] ; then
        mkdir -p $WCWC_PREFIX
    fi
}

@test "wcwc exists with version" {
    run -0 wcwc version
    [[ -n "$output" ]]
}

@test "init spack" {
    # must use develop until 0.23 is released for {namespace} support
    run -0 wcwc admin init --tag develop spack
    [[ -f $WCWC_PREFIX/spack/bin/spack ]]
    # [[ -d $WCWC_PREFIX/.spack/bootstrap ]]
}

@test "install zlib" {
    run -0 wcwc admin install zlib
    [[ -n "$(wcwc find zlib | grep ^zlib)" ]]
}

@test "make a system environment" {
    run -0 wcwc env -e test-system-env --target spack zlib
    local edir=$WCWC_PREFIX/stacks/spack/environments/test-system-env
    [[ -d "$edir" ]]
    run grep -q '\bzlib\b' "$edir/spack.yaml"
    test -L $edir/.spack-env/._view/*/lib/libz.so
}

@test "use a system environment" {
    run -0 wcwc shell -e test-system-env -c 'spack find zlib'
}

@test "make a user environment" {
    run -0 wcwc env -e $WCWC_PREFIX/test-user-env  zlib
    local edir=$WCWC_PREFIX/test-user-env
    [[ -d "$edir" ]]
    run grep -q '\bzlib\b' "$edir/spack.yaml"
    test -L $edir/.spack-env/._view/*/lib/libz.so
}

@test "use a user environment" {
    run -0 wcwc shell -e $WCWC_PREFIX/test-user-env -c 'spack find zlib'
}

teardown_file () {
    rm -rf $BATS_TMPDIR/wcwc-testing/native
}
