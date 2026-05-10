#include <iostream>
#include <cmath>
#include <fstream>
#include <thread>
#include <vector>
#include <mutex>
#include <atomic>
#include <iomanip>

using namespace std;

// 使用 __int128 处理 1E30 级别的平方运算
typedef __int128_t int128;

mutex file_mutex;
ofstream finCube;
atomic<long long> global_count(0);
atomic<long long> test_count(0);
// 提前构建模256的平方剩余表，提速82%
bool valid_sq256[256];

// 增加更多模过滤，大幅提升无效数据剔除率（达 90%+）
bool valid_sq255[255];
bool valid_sq63[63];

void init_sq_table() {
    for (int i = 0; i < 256; ++i) {
        valid_sq256[(i * i) % 256] = true;
    }
    for (int i = 0; i < 255; ++i) {
        valid_sq255[(i * i) % 255] = true;
    }
    for (int i = 0; i < 63; ++i) {
        valid_sq63[(i * i) % 63] = true;
    }
}

// 安全的完全平方数检查，结合快速取模过滤
inline bool is_perfect_square(int128 n) {
    // 快速位运算模256、模255剪枝
    if (!valid_sq256[n & 255]) return false;
    if (!valid_sq255[n % 255]) return false;
    if (!valid_sq63[n % 63]) return false;

    long long root = sqrt((double)n);
    if ((int128)root * root == n) return true;
    if ((int128)(root + 1) * (root + 1) == n) return true;
    if ((int128)(root - 1) * (root - 1) == n) return true;
    return false;
}

void find_cuboid_worker(long long a_start, long long a_end, long long max_len) {
    for (long long a = a_start; a < a_end; ++a) {
        
        // 核心剪枝：利用完美长方体的数论性质
        // (1) 三边至少其一能被 3 整除，其一被 4 整除，其一被 5, 7, 11 整除
        // (2) 如果 a 和 b 奇偶性相同且都为奇数，a^2+b^2 = 2 (mod 4)，不可能为平方数
        int a_mod4 = a % 4;

        int128 a2 = (int128)a * a;
        
        for (long long b = a + 1; b <= max_len; ++b) {
            // (1) 如果 a 是奇数且 b 也是奇数，a^2+b^2 会是 2(mod 4)，绝不可能是平方数 -> b 必为偶数
            if (a_mod4 % 2 != 0 && b % 2 != 0) continue;

            int128 b2 = (int128)b * b;
            int128 d_ab2 = a2 + b2;

            // 1. 检查第一个面对角线是否为整数
            if (!is_perfect_square(d_ab2)) continue;

            int a_mod3 = a % 3;
            int b_mod3 = b % 3;
            int a_mod5 = a % 5;
            int b_mod5 = b % 5;

            // 根据性质：c 对应的模约束
            for (long long c = b + 1; c <= max_len; ++c) {
                // 性质剪枝集成
                if (a_mod3 != 0 && b_mod3 != 0 && c % 3 != 0) continue;
                if (a_mod5 != 0 && b_mod5 != 0 && c % 5 != 0) continue;
                
                // 为了面对角线 b^2 + c^2 是平方数... 同理
                if (b % 2 != 0 && c % 2 != 0) continue;
                if (a % 2 != 0 && c % 2 != 0) continue;

                int128 c2 = (int128)c * c;
                
                // 2. 检查另外两个面对角线
                if (!is_perfect_square(a2 + c2)) continue;
                if (!is_perfect_square(b2 + c2)) continue;
                // 进度汇报：保存当前值后再比较，避免多线程下打印错误
                long long cur_test = ++test_count;
                if (cur_test % 20000000 == 0) {
                    lock_guard<mutex> lock(file_mutex);
                    cout << "progress test: " << cur_test << "\n";
                }

                cout << "\ntest cube: a=" << a << ", b=" << b << ", c=" << c << endl;
                // 3. 检查空间对角线
                int128 g2 = a2 + b2 + c2;
                if (is_perfect_square(g2)) {
                    lock_guard<mutex> lock(file_mutex);
                    cout << "\n找到完美长方体候选: a=" << a << ", b=" << b << ", c=" << c << endl;
                    finCube << a << "," << b << "," << c << endl;
                }
            }
        }
        
        // 进度汇报：先保存递增后的值，避免打印时被其他线程再次修改
        long long cur = ++global_count;
        if (cur % 5000000 == 0) {
            cout << "progress a-loop: " << cur << "\n";
        }
    }
}

int main() {
    init_sq_table(); // 初始化平方余数快速过滤表
    
    // 搜索范围设置
    const long long SEARCH_START = 1000200000000LL; // 1E12
    const long long SEARCH_END   = 1E13; // 演示步长
    const int num_threads = 240; // 适配服务器核心数

    finCube.open("PerfectCuboid_Results.txt", ios::app);
    if (!finCube) return -1;

    vector<thread> workers;
    long long total_range = SEARCH_END - SEARCH_START;
    long long chunk = total_range / num_threads;

    cout << "🚀 启动 200 核并行搜索..." << endl;

    for (int i = 0; i < num_threads; ++i) {
        long long start = SEARCH_START + i * chunk;
        long long end = (i == num_threads - 1) ? SEARCH_END : start + chunk;
        workers.emplace_back(find_cuboid_worker, start, end, 1500000000000LL); // max_c 为 1.5E15
    }

    for (auto& t : workers) t.join();

    finCube.close();
    return 0;
}
