timeman.o: timeman.cpp timeman.h misc.h search.h history.h memory.h \
 types.h tune.h position.h attacks.h bitboard.h nnue/nnue_accumulator.h \
 nnue/../types.h nnue/../tune.h nnue/../misc.h nnue/nnue_architecture.h \
 nnue/features/k32h3.h nnue/features/../../misc.h \
 nnue/features/../../types.h nnue/features/../../tune.h \
 nnue/features/../nnue_common.h nnue/features/../../misc.h \
 nnue/features/../../types.h nnue/features/full_threats.h \
 nnue/features/pp_3wide.h nnue/layers/affine_transform.h \
 nnue/layers/../../memory.h nnue/layers/../nnue_common.h \
 nnue/layers/../simd.h nnue/layers/../../types.h nnue/layers/../../tune.h \
 nnue/layers/../nnue_common.h nnue/layers/affine_transform_sparse_input.h \
 nnue/layers/../../bitboard.h nnue/layers/../nnz_helper.h \
 nnue/layers/../simd.h nnue/layers/clipped_relu.h \
 nnue/layers/sqr_clipped_relu.h nnue/nnue_common.h nnue/nnz_helper.h \
 numa.h shm.h shm_unix.h thread_native.h score.h smother.h \
 syzygy/tbprobe.h ucioption.h
timeman.h:
misc.h:
search.h:
history.h:
memory.h:
types.h:
tune.h:
position.h:
attacks.h:
bitboard.h:
nnue/nnue_accumulator.h:
nnue/../types.h:
nnue/../tune.h:
nnue/../misc.h:
nnue/nnue_architecture.h:
nnue/features/k32h3.h:
nnue/features/../../misc.h:
nnue/features/../../types.h:
nnue/features/../../tune.h:
nnue/features/../nnue_common.h:
nnue/features/../../misc.h:
nnue/features/../../types.h:
nnue/features/full_threats.h:
nnue/features/pp_3wide.h:
nnue/layers/affine_transform.h:
nnue/layers/../../memory.h:
nnue/layers/../nnue_common.h:
nnue/layers/../simd.h:
nnue/layers/../../types.h:
nnue/layers/../../tune.h:
nnue/layers/../nnue_common.h:
nnue/layers/affine_transform_sparse_input.h:
nnue/layers/../../bitboard.h:
nnue/layers/../nnz_helper.h:
nnue/layers/../simd.h:
nnue/layers/clipped_relu.h:
nnue/layers/sqr_clipped_relu.h:
nnue/nnue_common.h:
nnue/nnz_helper.h:
numa.h:
shm.h:
shm_unix.h:
thread_native.h:
score.h:
smother.h:
syzygy/tbprobe.h:
ucioption.h:

saved_cmd_timeman.o :=    'g++ -Wall -Wcast-qual -fno-exceptions -std=c++17 -pedantic -Wextra -Wshadow -Wmissing-declarations -m64 -Wstack-usage=128000 -fno-ipa-cp-clone -DNDEBUG -O3 -funroll-loops -fno-stack-protector -DIS_64BIT -msse -msse3 -mpopcnt -DUSE_POPCNT -DUSE_AVX2 -mavx2 -mbmi -DUSE_SSE41 -msse4.1 -DUSE_SSSE3 -mssse3 -DUSE_SSE2 -msse2 -DARCH=x86-64-avx2 -flto -flto-partition=one -MMD -MP -MF "./.timeman.o.cmd.tmp" -MQ "timeman.o" -c -o timeman.o timeman.cpp' '/usr/bin/x86_64-linux-gnu-g++-13' 'g++ (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0 Copyright (C) 2023 Free Software Foundation, Inc. This is free software; see the source for copying conditions.  There is NO warranty; not even for MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.'

   timeman.cpp:
