#!/bin/bash
# Build static Android arm64 binaries for DroidFish with NDK r27c.
set -e
S=/tmp/claude-0/-home-user-Smotherfish/e1fa86d3-745c-55ff-be7c-77b42a0872f8/scratchpad
NDK=$S/tools/android-ndk-r27c/toolchains/llvm/prebuilt/linux-x86_64/bin
OUT=${OUT:-/home/user/Smotherfish/android}
mkdir -p $OUT
cd /home/user/Smotherfish/src
for arch in armv8-dotprod armv8; do
  make objclean >/dev/null
  PATH=$NDK:$PATH make -j4 build ARCH=$arch COMP=ndk EXTRALDFLAGS="-static" > $S/ndk_$arch.log 2>&1
  $NDK/llvm-strip stockfish
  mv stockfish $OUT/smotherfish-$arch
done
make objclean >/dev/null
file $OUT/*
