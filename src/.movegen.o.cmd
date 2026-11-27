movegen.o: movegen.cpp movegen.h misc.h types.h tune.h attacks.h \
 bitboard.h position.h
movegen.h:
misc.h:
types.h:
tune.h:
attacks.h:
bitboard.h:
position.h:

saved_cmd_movegen.o :=    'g++ -Wall -Wcast-qual -fno-exceptions -std=c++17 -pedantic -Wextra -Wshadow -Wmissing-declarations -m64 -Wstack-usage=128000 -fno-ipa-cp-clone -DNDEBUG -O3 -funroll-loops -fno-stack-protector -DIS_64BIT -msse -msse3 -mpopcnt -DUSE_POPCNT -DUSE_AVX2 -mavx2 -mbmi -DUSE_SSE41 -msse4.1 -DUSE_SSSE3 -mssse3 -DUSE_SSE2 -msse2 -DARCH=x86-64-avx2 -flto -flto-partition=one -MMD -MP -MF "./.movegen.o.cmd.tmp" -MQ "movegen.o" -c -o movegen.o movegen.cpp' '/usr/bin/x86_64-linux-gnu-g++-13' 'g++ (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0 Copyright (C) 2023 Free Software Foundation, Inc. This is free software; see the source for copying conditions.  There is NO warranty; not even for MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.'

   movegen.cpp:
