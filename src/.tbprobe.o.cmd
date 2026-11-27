tbprobe.o: syzygy/tbprobe.cpp syzygy/tbprobe.h syzygy/../attacks.h \
 syzygy/../misc.h syzygy/../types.h syzygy/../tune.h syzygy/../bitboard.h \
 syzygy/../bitboard.h syzygy/../misc.h syzygy/../movegen.h \
 syzygy/../position.h syzygy/../attacks.h syzygy/../search.h \
 syzygy/../history.h syzygy/../memory.h syzygy/../position.h \
 syzygy/../nnue/nnue_accumulator.h syzygy/../nnue/../types.h \
 syzygy/../nnue/../tune.h syzygy/../nnue/../misc.h \
 syzygy/../nnue/nnue_architecture.h syzygy/../nnue/features/k32h3.h \
 syzygy/../nnue/features/../../misc.h \
 syzygy/../nnue/features/../../types.h \
 syzygy/../nnue/features/../../tune.h \
 syzygy/../nnue/features/../nnue_common.h \
 syzygy/../nnue/features/../../misc.h \
 syzygy/../nnue/features/../../types.h \
 syzygy/../nnue/features/full_threats.h \
 syzygy/../nnue/features/pp_3wide.h \
 syzygy/../nnue/layers/affine_transform.h \
 syzygy/../nnue/layers/../../memory.h \
 syzygy/../nnue/layers/../nnue_common.h syzygy/../nnue/layers/../simd.h \
 syzygy/../nnue/layers/../../types.h syzygy/../nnue/layers/../../tune.h \
 syzygy/../nnue/layers/../nnue_common.h \
 syzygy/../nnue/layers/affine_transform_sparse_input.h \
 syzygy/../nnue/layers/../../bitboard.h \
 syzygy/../nnue/layers/../nnz_helper.h syzygy/../nnue/layers/../simd.h \
 syzygy/../nnue/layers/clipped_relu.h \
 syzygy/../nnue/layers/sqr_clipped_relu.h syzygy/../nnue/nnue_common.h \
 syzygy/../nnue/nnz_helper.h syzygy/../numa.h syzygy/../shm.h \
 syzygy/../shm_unix.h syzygy/../thread_native.h syzygy/../score.h \
 syzygy/../smother.h syzygy/../syzygy/tbprobe.h syzygy/../timeman.h \
 syzygy/../types.h syzygy/../ucioption.h
syzygy/tbprobe.h:
syzygy/../attacks.h:
syzygy/../misc.h:
syzygy/../types.h:
syzygy/../tune.h:
syzygy/../bitboard.h:
syzygy/../bitboard.h:
syzygy/../misc.h:
syzygy/../movegen.h:
syzygy/../position.h:
syzygy/../attacks.h:
syzygy/../search.h:
syzygy/../history.h:
syzygy/../memory.h:
syzygy/../position.h:
syzygy/../nnue/nnue_accumulator.h:
syzygy/../nnue/../types.h:
syzygy/../nnue/../tune.h:
syzygy/../nnue/../misc.h:
syzygy/../nnue/nnue_architecture.h:
syzygy/../nnue/features/k32h3.h:
syzygy/../nnue/features/../../misc.h:
syzygy/../nnue/features/../../types.h:
syzygy/../nnue/features/../../tune.h:
syzygy/../nnue/features/../nnue_common.h:
syzygy/../nnue/features/../../misc.h:
syzygy/../nnue/features/../../types.h:
syzygy/../nnue/features/full_threats.h:
syzygy/../nnue/features/pp_3wide.h:
syzygy/../nnue/layers/affine_transform.h:
syzygy/../nnue/layers/../../memory.h:
syzygy/../nnue/layers/../nnue_common.h:
syzygy/../nnue/layers/../simd.h:
syzygy/../nnue/layers/../../types.h:
syzygy/../nnue/layers/../../tune.h:
syzygy/../nnue/layers/../nnue_common.h:
syzygy/../nnue/layers/affine_transform_sparse_input.h:
syzygy/../nnue/layers/../../bitboard.h:
syzygy/../nnue/layers/../nnz_helper.h:
syzygy/../nnue/layers/../simd.h:
syzygy/../nnue/layers/clipped_relu.h:
syzygy/../nnue/layers/sqr_clipped_relu.h:
syzygy/../nnue/nnue_common.h:
syzygy/../nnue/nnz_helper.h:
syzygy/../numa.h:
syzygy/../shm.h:
syzygy/../shm_unix.h:
syzygy/../thread_native.h:
syzygy/../score.h:
syzygy/../smother.h:
syzygy/../syzygy/tbprobe.h:
syzygy/../timeman.h:
syzygy/../types.h:
syzygy/../ucioption.h:

saved_cmd_tbprobe.o :=    'g++ -Wall -Wcast-qual -fno-exceptions -std=c++17 -pedantic -Wextra -Wshadow -Wmissing-declarations -m64 -Wstack-usage=128000 -fno-ipa-cp-clone -DNDEBUG -O3 -funroll-loops -fno-stack-protector -DIS_64BIT -msse -msse3 -mpopcnt -DUSE_POPCNT -DUSE_AVX2 -mavx2 -mbmi -DUSE_SSE41 -msse4.1 -DUSE_SSSE3 -mssse3 -DUSE_SSE2 -msse2 -DARCH=x86-64-avx2 -flto -flto-partition=one -MMD -MP -MF "./.tbprobe.o.cmd.tmp" -MQ "tbprobe.o" -c -o tbprobe.o syzygy/tbprobe.cpp' '/usr/bin/x86_64-linux-gnu-g++-13' 'g++ (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0 Copyright (C) 2023 Free Software Foundation, Inc. This is free software; see the source for copying conditions.  There is NO warranty; not even for MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.'

   syzygy/tbprobe.cpp:
