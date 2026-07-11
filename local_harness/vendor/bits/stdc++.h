// Portability shim for <bits/stdc++.h> (a GCC-only convenience header) so
// competitive-programming sources compile under Apple clang / libc++ locally.
// Polygon's judge uses real g++ where this header exists natively; this shim
// only affects LOCAL harness compilation. It pulls in the commonly-used STL.
#ifndef LOCAL_HARNESS_BITS_STDCXX_H
#define LOCAL_HARNESS_BITS_STDCXX_H

#include <algorithm>
#include <array>
#include <bitset>
#include <cassert>
#include <cctype>
#include <cfloat>
#include <climits>
#include <cmath>
#include <complex>
#include <cstdarg>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <deque>
#include <exception>
#include <functional>
#include <initializer_list>
#include <iomanip>
#include <ios>
#include <iostream>
#include <istream>
#include <iterator>
#include <limits>
#include <list>
#include <map>
#include <memory>
#include <numeric>
#include <ostream>
#include <queue>
#include <random>
#include <set>
#include <sstream>
#include <stack>
#include <stdexcept>
#include <string>
#include <tuple>
#include <type_traits>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

#endif  // LOCAL_HARNESS_BITS_STDCXX_H
