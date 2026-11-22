```
1000 won games (ours == 1.0)
  full            93   9.3%  true smother delivered
  missed         149  14.9%  forced true smother existed, engine claimed no proof there
  unconverted     21   2.1%  engine claimed a proof there, no true smother followed
  never          737  73.7%  no forced true smother in any winning position checked

forced true smother available at some point: 263 ( 26.3%)
  mate-in at first availability: median 8, <=4: 41, 5-8: 155, >8: 67
  normal prover limits (8 moves, 1 quiet, 5M) also find it: 152 of 263
  eval at availability (cp, mate=100000): median 100000, >=1000 or mate: 260 of 263
  plies from first winning position to availability: median 44

missed: 149 games; engine proof later in the game: 127; ended in a near smother: 107; small limits find it: 65

unconverted: 21 games; engine proof later in the game: 17; ended in a near smother: 16; small limits find it: 17

never: 737 games; ended in a near smother: 339; winning positions checked per game: median 56
  defender pieces (non-king) at first winning position: median 12 (full games: 12)
  plies from first winning position to the end: median 115

CPU seconds per game: median 189
```
