#!/bin/bash
# Should be run through go/benz

set -eux

cd git/benz-build-source
sudo kokoro/setup.sh
sudo apt-get install tree

FAUCET_VERSION=$(< etc/FAUCET_VERSION)
echo Fixing debian faucet version to $FAUCET_VERSION
fgrep -v $FAUCET_VERSION debian/control > /dev/null
sed -i s/FAUCET_VERSION/${FAUCET_VERSION}/ debian/control
fgrep $FAUCET_VERSION debian/control

VERSION=$(git describe)
debchange --newversion $VERSION -b "New upstream release"

# Write version content to __version__.py
cat >forch/__version__.py <<VER_FILE
"""Forch version file"""

__version__ = '$VERSION'
VER_FILE

cat forch/__version__.py
build-debs -b -L -d rodete

(
    cd esdn-faucet
    git checkout origin/esdn -- FORCH_VERSION
    FORCH_VERSION=$(< FORCH_VERSION)
    echo Fixing debian forch version to $FORCH_VERSION
    fgrep -v $FORCH_VERSION debian/control > /dev/null
    sed -i s/FORCH_VERSION/${FORCH_VERSION}/ debian/control
    fgrep $FORCH_VERSION debian/control

    VERSION=$(git describe remotes/origin/esdn)
    echo esdn-faucet version $VERSION
    debchange --newversion $VERSION -b "New upstream release"
    build-debs -b -L -d rodete
)

cp esdn-faucet/binary/* binary/
ls -l binary/