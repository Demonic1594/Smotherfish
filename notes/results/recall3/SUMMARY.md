```
203 won games (ours == 1.0)
  full            14   6.9%  true smother delivered
  missed           8   3.9%  forced true smother existed, engine claimed no proof there
  unconverted     15   7.4%  engine claimed a proof there, no true smother followed
  never          166  81.8%  no forced true smother in any winning position checked

forced true smother available at some point: 37 ( 18.2%)
  mate-in at first availability: median 8, <=4: 0, 5-8: 30, >8: 7
  normal prover limits (8 moves, 1 quiet, 5M) also find it: 18 of 37
  eval at availability (cp, mate=100000): median 100000, >=1000 or mate: 37 of 37
  plies from first winning position to availability: median 40

missed: 8 games; engine proof later in the game: 7; ended in a near smother: 5; small limits find it: 1

unconverted: 15 games; engine proof later in the game: 10; ended in a near smother: 11; small limits find it: 11

never: 166 games; ended in a near smother: 63; winning positions checked per game: median 46
  defender pieces (non-king) at first winning position: median 10 (full games: 12)
  plies from first winning position to the end: median 93

CPU seconds per game: median 182
```
