```
600 won games (ours == 1.0)
  full            53   8.8%  true smother delivered
  missed           0   0.0%  forced true smother existed, engine claimed no proof there
  unconverted      2   0.3%  engine claimed a proof there, no true smother followed
  never          545  90.8%  no forced true smother in any winning position checked

forced true smother available at some point: 55 (  9.2%)
  mate-in at first availability: median 2, <=4: 49, 5-8: 3, >8: 3
  normal prover limits (8 moves, 1 quiet, 5M) also find it: 51 of 55
  eval at availability (cp, mate=100000): median 100000, >=1000 or mate: 55 of 55
  plies from first winning position to availability: median 54

unconverted: 2 games; engine proof later in the game: 2; ended in a near smother: 2; small limits find it: 0

never: 545 games; ended in a near smother: 273; winning positions checked per game: median 54
  defender pieces (non-king) at first winning position: median 12 (full games: 13)
  plies from first winning position to the end: median 107

CPU seconds per game: median 142
```
