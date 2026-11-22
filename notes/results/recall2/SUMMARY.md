```
288 won games (ours == 1.0)
  full            34  11.8%  true smother delivered
  missed          29  10.1%  forced true smother existed, engine claimed no proof there
  unconverted     31  10.8%  engine claimed a proof there, no true smother followed
  never          194  67.4%  no forced true smother in any winning position checked

forced true smother available at some point: 94 ( 32.6%)
  mate-in at first availability: median 7, <=4: 12, 5-8: 64, >8: 18
  normal prover limits (8 moves, 1 quiet, 5M) also find it: 53 of 94
  eval at availability (cp, mate=100000): median 100000, >=1000 or mate: 94 of 94
  plies from first winning position to availability: median 43

missed: 29 games; engine proof later in the game: 27; ended in a near smother: 21; small limits find it: 3

unconverted: 31 games; engine proof later in the game: 30; ended in a near smother: 28; small limits find it: 29

never: 194 games; ended in a near smother: 116; winning positions checked per game: median 49
  defender pieces (non-king) at first winning position: median 12 (full games: 12)
  plies from first winning position to the end: median 97

CPU seconds per game: median 194
```
