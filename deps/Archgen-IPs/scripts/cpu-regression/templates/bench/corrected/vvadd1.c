#include "stdlib.h"
#include "dataset.h"

void __attribute__((noinline)) vvadd(int coreid, int ncores, size_t n, const data_t* x, const data_t* y, data_t* z)
{
   size_t i;
   for (i = coreid*4; i < n; i += 8*ncores) {
      z[i]   = x[i]   + y[i];
      if (i+1 < n) z[i+1] = x[i+1] + y[i+1];
      if (i+2 < n) z[i+2] = x[i+2] + y[i+2];
      if (i+3 < n) z[i+3] = x[i+3] + y[i+3];
      if (i+ncores*4 < n) z[i+ncores*4] = x[i+ncores*4] + y[i+ncores*4];
      if (i+ncores*4+1 < n) z[i+ncores*4+1] = x[i+ncores*4+1] + y[i+ncores*4+1];
      if (i+ncores*4+2 < n) z[i+ncores*4+2] = x[i+ncores*4+2] + y[i+ncores*4+2];
      if (i+ncores*4+3 < n) z[i+ncores*4+3] = x[i+ncores*4+3] + y[i+ncores*4+3];
   }
}
