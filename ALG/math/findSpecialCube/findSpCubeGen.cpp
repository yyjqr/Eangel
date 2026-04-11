#include <iostream>
#include <vector>
#include <cmath>
#include <thread>
#include <mutex>
#include <atomic>
#include <numeric>
#include <fstream>
#include <algorithm>

using namespace std;

using u64 = uint64_t;
using u128 = __uint128_t;

constexpr u64 EDGE_MIN = 6000000000000ULL; // 1E12 -->3E12
constexpr u64 EDGE_MAX = 10000000000000ULL; // 1E13
constexpr char OUTPUT_FILE[] = "PerfectCuboid_GenResults.txt";

mutex io_mutex;
ofstream result_file;
atomic<u64> global_u_checked(0);

u64 floor_sqrt_u64(u64 x) {
    return std::sqrt(static_cast<double>(x));
}

u64 floor_sqrt_u128(u128 value) {
    if (value == 0) return 0;
    u64 root = std::sqrt(static_cast<double>(value));
    while ((u128)(root + 1) * (root + 1) <= value) ++root;
    while ((u128)root * root > value) --root;
    return root;
}

bool is_perfect_square(u128 value, u64* root = nullptr) {
    u64 candidate = floor_sqrt_u128(value);
    if ((u128)candidate * candidate != value) return false;
    if (root) *root = candidate;
    return true;
}

vector<pair<u64, int>> factorize(u64 n) {
    if (n == 0) return {};
    vector<pair<u64, int>> factors;
    for (u64 d = 2; d * d <= n; ++d) {
        if (n % d == 0) {
            int exponent = 0;
            while (n % d == 0) {
                ++exponent;
                n /= d;
            }
            factors.push_back({d, exponent});
        }
    }
    if (n > 1) {
        factors.push_back({n, 1});
    }
    return factors;
}

vector<pair<u64, int>> merge_factors(const vector<pair<u64, int>>& f1, const vector<pair<u64, int>>& f2) {
    vector<pair<u64, int>> merged = f1;
    for (const auto& f : f2) {
        auto it = find_if(merged.begin(), merged.end(), [&f](const pair<u64, int>& p) { return p.first == f.first; });
        if (it != merged.end()) {
            it->second += f.second;
        } else {
            merged.push_back(f);
        }
    }
    return merged;
}

void get_divisors(const vector<pair<u64, int>>& factors, int idx, u128 current, vector<u128>& div) {
    if (idx == factors.size()) {
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
            if (std::gcd(u, v) != 1) continue;

            u64 a_prime = u * u - v * v;
            u64 b_prime = 2 * u * v;
            u64 m_prime = u * u + v * v;
            u64 x = min(a_prime, b_prime); // smaller base edge
            u64 y = max(a_prime, b_prime); // larger base edge

            // Check if bounds have any overlap
            // max(k*x, k*y) in [EDGE_MIN, EDGE_MAX] => k*y in [EDGE_MIN, EDGE_MAX]
            u64 k_min = (EDGE_MIN + y - 1) / y;
            u64 k_max = EDGE_MAX / y;
            
            // 核心修复: 截断大 k 导致的性能黑洞！
            // 如果生成的基础边 y 极小 (比如 4)，k 会高达万亿级，在对大 k 循环并质因数分解时会彻底卡死。
            // 事实上，如果某个完美长方体是大倍数缩放而来的，它对应的本原极小完美长方体早就被前人发现了。
            // 既然我们要找 1E12 以上的未知解，我们只能（也只需）搜索全新的本原解！
            // 严格限制 k_max 最多为 10（稍微冗余），拒绝把小三角放大千亿倍！
            k_max = min(k_max, 10UL);
            
            if (k_min > k_max) continue;

            auto f_y_minus_x = factorize(y - x);
            auto f_y_plus_x = factorize(y + x);
            auto f_base = merge_factors(f_y_minus_x, f_y_plus_x); // factors of y^2 - x^2

            for (u64 k = k_min; k <= k_max; ++k) {
                u64 a = k * x;
                u64 b = k * y;
                u64 m = k * m_prime;

                auto f_k = factorize(k);
                auto f_k2 = f_k;
                for (auto& pf : f_k2) pf.second *= 2; // k^2
                auto f_total = merge_factors(f_base, f_k2); // complete factors of b^2 - a^2

                vector<u128> divisors;
                get_divisors(f_total, 0, 1, divisors);
                 {
                //lock_guard<mutex> lock(io_mutex);
                //cout << "1st test k:"<< k << "a|b:"<<a <<"," <<b <<endl;
                }
                u128 diff = (u128)b * b - (u128)a * a;
                for (u128 d1 : divisors) {
                    u128 d2 = diff / d1;
                    if (d1 >= d2) continue; // o < n, so d1 < d2
                    
                    if ((d1 % 2) != (d2 % 2)) continue; // n, o must be integer

                    u128 o = (d2 - d1) / 2;
                    u128 n = (d1 + d2) / 2;
                    
                    if (n <= b) continue;

                    u128 c2 = n * n - (u128)b * b;
                    if (c2 == 0) continue;
                    //if(c2 != 0){
                    //  lock_guard<mutex> lock(io_mutex);
                    //  cout <<setw(3)<< "test k:"<< k << "a|b:"<<a <<"," <<b <<endl;
                    //}
                    u64 c = 0;
                    if (!is_perfect_square(c2, &c)) continue;
                    //cout <<"test c2" << c2<<"\n";
                    cout << "2nd test k:"<< k << "a|b|c:"<<a <<"," <<b <<","<<c <<endl;
                    // Final check: space diagonal
                    u128 p2 = (u128)m * m + c2;
                    u64 p = 0;
                    if (is_perfect_square(p2, &p)) {
                        lock_guard<mutex> lock(io_mutex);
                        cout << "--- FOUND CUBE! --- a=" << a << " b=" << b << " c=" << c << "\n";
                        result_file << a << ',' << b << ',' << c << '\n';
                    }
                }
            }
        }
    }
}

int main() {
    result_file.open(OUTPUT_FILE, ios::app);
    u64 max_u = std::sqrt(EDGE_MAX) + 1;
    cout << "Start Gen Strategy, max_u=" << max_u << "\n";

    int num_threads = thread::hardware_concurrency();
    if (num_threads == 0) num_threads = 16;
    vector<thread> workers;

    u64 chunk = (max_u - 1) / num_threads + 1;
    for (int i = 0; i < num_threads; ++i) {
        u64 start = 2 + i * chunk;
        u64 end = min(max_u + 1, start + chunk);
        if (start < end) {
            workers.emplace_back(worker, start, end);
        }
    }

    for (auto& w : workers) w.join();
    result_file.close();
    cout << "Finished.\n";
    return 0;
}
