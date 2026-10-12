#include <algorithm>
#include <atomic>
#include <cmath>
#include <fstream>
#include <iostream>
#include <mutex>
#include <numeric>
#include <thread>
#include <vector>

using namespace std;

using u64 = uint64_t;
using u128 = __uint128_t;

constexpr u64 EDGE_MIN =
    9000000000000ULL; // 1E12 -->3E12--->（1011  6E12--->9E12)
constexpr u64 EDGE_MAX = 100000000000000ULL; // 1E13---》1E14
constexpr char OUTPUT_FILE[] = "PerfectCuboid_GenResults.txt";

mutex io_mutex;
ofstream result_file;
atomic<u64> global_u_checked(0);

u64 floor_sqrt_u128(u128 value) {
  if (value == 0)
    return 0;
  u64 root = std::sqrt(static_cast<double>(value));
  while ((u128)(root + 1) * (root + 1) <= value)
    ++root;
  while ((u128)root * root > value)
    --root;
  return root;
}

bool is_perfect_square(u128 value, u64 *root = nullptr) {
  u64 candidate = floor_sqrt_u128(value);
  if ((u128)candidate * candidate != value)
    return false;
  if (root)
    *root = candidate;
  return true;
}

// ── Miller–Rabin + Pollard–Rho 快速因数分解 ──────────────────────────────────

// 128 位模乘，避免 64 位乘法溢出
inline u64 mulmod64(u64 a, u64 b, u64 m) {
  return static_cast<u128>(a) * b % m;
}

// 快速模幂
static u64 powmod64(u64 a, u64 b, u64 m) {
  u64 res = 1 % m;
  for (a %= m; b; b >>= 1, a = mulmod64(a, a, m))
    if (b & 1)
      res = mulmod64(res, a, m);
  return res;
}

// 确定性 Miller–Rabin：对所有 64 位整数无误判
// 底数集合 {2,3,5,7,11,13,17,19,23,29,31,37} 覆盖 n < 3.3×10^24
static bool is_prime64(u64 n) {
  if (n < 2)
    return false;
  if (n == 2 || n == 3 || n == 5 || n == 7)
    return true;
  if (n % 2 == 0 || n % 3 == 0 || n % 5 == 0)
    return false;
  u64 d = n - 1;
  int r = 0;
  while (!(d & 1)) {
    d >>= 1;
    ++r;
  }
  for (u64 a : {2ULL, 3ULL, 5ULL, 7ULL, 11ULL, 13ULL, 17ULL, 19ULL, 23ULL,
                29ULL, 31ULL, 37ULL}) {
    if (a >= n)
      continue;
    u64 x = powmod64(a, d, n);
    if (x == 1 || x == n - 1)
      continue;
    bool composite = true;
    for (int i = 0; i < r - 1; ++i) {
      x = mulmod64(x, x, n);
      if (x == n - 1) {
        composite = false;
        break;
      }
    }
    if (composite)
      return false;
  }
  return true;
}

// Pollard–Rho（Floyd 判圈）；n 必须是合数
// 返回 n 的一个非平凡因子，或 n（判圈失败，调用方换 c 重试）
static u64 pollard_rho(u64 n, u64 c) {
  auto f = [&](u64 x) { return (mulmod64(x, x, n) + c) % n; };
  u64 x = 2, y = 2, d = 1;
  while (d == 1) {
    x = f(x);
    y = f(f(y));
    u64 diff = x > y ? x - y : y - x;
    d = std::gcd(diff, n);
    if (x == y)
      return n; // 进入循环，换参数重试
  }
  return d;
}

// 递归分解：将 n 的所有素因子累积到 out
static void factorize_impl(u64 n, vector<pair<u64, int>> &out) {
  if (n == 1)
    return;
  if (is_prime64(n)) {
    auto it = find_if(out.begin(), out.end(),
                      [n](const pair<u64, int> &p) { return p.first == n; });
    if (it != out.end()) {
      ++it->second;
    } else {
      out.push_back({n, 1});
    }
    return;
  }
  // 寻找非平凡因子，失败时递增 c
  u64 d = n;
  for (u64 c = 1; d == n || d <= 1; ++c)
    d = pollard_rho(n, c);
  factorize_impl(d, out);
  factorize_impl(n / d, out);
}

// 公开接口：先用小素数试除加速，再调用 Pollard–Rho 处理大因子
vector<pair<u64, int>> factorize(u64 n) {
  if (n == 0)
    return {};
  vector<pair<u64, int>> factors;
  for (u64 p : {2ULL, 3ULL, 5ULL, 7ULL, 11ULL, 13ULL, 17ULL, 19ULL}) {
    if (n % p == 0) {
      int e = 0;
      while (n % p == 0) {
        n /= p;
        ++e;
      }
      factors.push_back({p, e});
    }
  }
  factorize_impl(n, factors);
  return factors;
}

vector<pair<u64, int>> merge_factors(const vector<pair<u64, int>> &f1,
                                     const vector<pair<u64, int>> &f2) {
  vector<pair<u64, int>> merged = f1;
  for (const auto &f : f2) {
    auto it =
        find_if(merged.begin(), merged.end(),
                [&f](const pair<u64, int> &p) { return p.first == f.first; });
    if (it != merged.end()) {
      it->second += f.second;
    } else {
      merged.push_back(f);
    }
  }
  return merged;
}

void get_divisors(const vector<pair<u64, int>> &factors, int idx, u128 current,
                  vector<u128> &div) {
  if (idx == static_cast<int>(factors.size())) {
    div.push_back(current);
    return;
  }
  u128 val = current;
  for (int i = 0; i <= factors[idx].second; ++i) {
    get_divisors(factors, idx + 1, val, div);
    val *= factors[idx].first;
  }
}

void worker(u64 u_start, u64 u_end) {
  for (u64 u = u_start; u < u_end; ++u) {
    u64 u_checked = ++global_u_checked;
    if (u_checked % 10000 == 0) {
      lock_guard<mutex> lock(io_mutex);
      cout << "progress u: " << u_checked << " (current u=" << u << ")\n";
    }

    for (u64 v = 1 + (u % 2 == 0 ? 0 : 1); v < u; v += 2) {
      if (std::gcd(u, v) != 1)
        continue;

      u64 a_prime = u * u - v * v;
      u64 b_prime = 2 * u * v;
      u64 m_prime = u * u + v * v;
      u64 x = min(a_prime, b_prime); // smaller base edge
      u64 y = max(a_prime, b_prime); // larger base edge

      // Check if bounds have any overlap
      // max(k*x, k*y) in [EDGE_MIN, EDGE_MAX] => k*y in [EDGE_MIN, EDGE_MAX]
      u64 k_min = (EDGE_MIN + y - 1) / y;
      u64 k_max = EDGE_MAX / y;

      // k 的范围完全由边长区间 [EDGE_MIN, EDGE_MAX] 推导，不加任意上限。
      // 本原性判断在所有平方检验通过后通过 gcd(a,b,c)==1 完成，
      // 而非用单个面的缩放因子 k 作为代理（k 仅约束面 (a,b,m)，不约束 c）。
      // 注意：若 y 极小（如 4），k_max 可达万亿级，性能开销极大；
      // 如需加速可设置 K_CAP，但结果将不完整，需在输出中注明。

      if (k_min > k_max)
        continue;

      auto f_y_minus_x = factorize(y - x);
      auto f_y_plus_x = factorize(y + x);
      auto f_base =
          merge_factors(f_y_minus_x, f_y_plus_x); // factors of y^2 - x^2

      for (u64 k = k_min; k <= k_max; ++k) {
        u64 a = k * x;
        u64 b = k * y;
        u64 m = k * m_prime;

        auto f_k = factorize(k);
        auto f_k2 = f_k;
        for (auto &pf : f_k2)
          pf.second *= 2; // k^2
        auto f_total =
            merge_factors(f_base, f_k2); // complete factors of b^2 - a^2

        vector<u128> divisors;
        get_divisors(f_total, 0, 1, divisors);
        {
          // lock_guard<mutex> lock(io_mutex);
          // cout << "1st test k:"<< k << "a|b:"<<a <<"," <<b <<endl;
        }
        u128 diff = (u128)b * b - (u128)a * a;
        for (u128 d1 : divisors) {
          u128 d2 = diff / d1;
          if (d1 >= d2)
            continue; // o < n, so d1 < d2

          if ((d1 % 2) != (d2 % 2))
            continue; // n, o must be integer

          u128 n = (d1 + d2) / 2;

          if (n <= b)
            continue;

          u128 c2 = n * n - (u128)b * b;
          if (c2 == 0)
            continue;
          // if(c2 != 0){
          //   lock_guard<mutex> lock(io_mutex);
          //   cout <<setw(3)<< "test k:"<< k << "a|b:"<<a <<"," <<b <<endl;
          // }
          u64 c = 0;
          if (!is_perfect_square(c2, &c))
            continue;
          // 本原长方体检验：gcd(a,b,c)==1
          // k 只约束面 (a,b,m)，不能代替对整体的本原性判断
          if (std::gcd(std::gcd(a, b), c) != 1)
            continue;
          {
            lock_guard<mutex> lock(io_mutex);
            cout << "2nd test k:" << k << "a|b|c:" << a << "," << b << "," << c
                 << endl;
            result_file << "maybe k:" << k << "a|b|c:" << a << "," << b << ","
                        << c << endl;
          }
          // Final check: space diagonal
          u128 p2 = (u128)m * m + c2;
          u64 p = 0;
          if (is_perfect_square(p2, &p)) {
            lock_guard<mutex> lock(io_mutex);
            cout << "--- FOUND CUBE! --- a=" << a << " b=" << b << " c=" << c
                 << "\n";
            result_file << a << ',' << b << ',' << c << '\n';
          }
        }
      }
    }
  }
}

int main() {
  result_file.open(OUTPUT_FILE, ios::app);
  if (!result_file.is_open()) {
    cerr << "Failed to open output file: " << OUTPUT_FILE << "\n";
    return 1;
  }
  // u 的正确上界：面斜边 m <= sqrt(2)*EDGE_MAX，且 u^2 < m，
  // 故 u < sqrt(sqrt(2)*EDGE_MAX)，用 ceil 保证不漏边界点
  const long double max_m =
      std::sqrt(2.0L) * static_cast<long double>(EDGE_MAX);
  const u64 u_end = static_cast<u64>(ceill(sqrtl(max_m)));
  cout << "Start Gen Strategy, u_end=" << u_end << "\n";

  int num_threads = thread::hardware_concurrency();
  if (num_threads == 0)
    num_threads = 16;
  vector<thread> workers;

  u64 chunk = (u_end - 2 + num_threads - 1) / num_threads;
  for (int i = 0; i < num_threads; ++i) {
    u64 start = 2 + i * chunk;
    u64 end = min(u_end, start + chunk);
    if (start < end) {
      workers.emplace_back(worker, start, end);
    }
  }

  for (auto &w : workers)
    w.join();
  result_file.close();
  cout << "Finished.\n";
  return 0;
}
