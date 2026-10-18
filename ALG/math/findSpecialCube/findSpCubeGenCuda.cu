#include <algorithm>
#include <atomic>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <mutex>
#include <numeric>
#include <shared_mutex>
#include <string>
#include <thread>
#include <unordered_map>
#include <vector>

#include <cuda_runtime.h>

using namespace std;

using u64 = uint64_t;
using u128 = __uint128_t;

constexpr u64 DEFAULT_EDGE_MIN = 9000000000000ULL;
constexpr u64 DEFAULT_EDGE_MAX = 100000000000000ULL;
constexpr char OUTPUT_FILE[] = "PerfectCuboid_GenResults_cuda.txt";
constexpr char EULER_OUTPUT_FILE[] = "EulerBrick_GenResults_cuda.txt";
constexpr char PROGRESS_FILE[] = "PerfectCuboid_Progress_cuda.txt";
constexpr u64 U_BATCH = 128;
constexpr u64 V_TILE = 1024;
constexpr int CUDA_THREADS = 256;
constexpr int PIPELINE_SLOTS = 2;
constexpr size_t FACTOR_CACHE_MAX_ENTRIES = 262144;
constexpr u64 PROGRESS_INTERVAL = 1000000ULL;

struct PrimitiveTask {
  u64 u;
  u64 v;
  u64 x;
  u64 y;
  u64 m;
  u64 k_min;
  u64 k_max;
};

struct CandidateTriplet {
  u64 a;
  u64 b;
  u64 c;
};

struct TileWindow {
  u64 u_begin;
  u64 u_end;
  u64 v_begin;
  u64 v_end;
};

struct PipelineSlot {
  cudaStream_t stream = nullptr;
  PrimitiveTask *device_tasks = nullptr;
  unsigned long long *device_count = nullptr;
  PrimitiveTask *host_tasks = nullptr;
  unsigned long long *host_count = nullptr;
  u64 capacity = 0;
  TileWindow tile{0, 0, 0, 0};
  bool active = false;
};

struct SearchStats {
  atomic<u64> primitive_pairs{0};
  atomic<u64> tasks_emitted{0};
  atomic<u64> k_values_checked{0};
  atomic<u64> divisor_pairs_checked{0};
  atomic<u64> square_hits{0};
  atomic<u64> factor_cache_hits{0};
  atomic<u64> factor_cache_misses{0};
  atomic<u64> factor_cache_inserts{0};
  atomic<u64> factor_cache_skips{0};
};

struct FactorCache {
  unordered_map<u64, vector<pair<u64, int>>> entries;
  mutable shared_mutex mutex;
};

mutex io_mutex;
ofstream result_file;
ofstream euler_result_file;
ofstream progress_file;
SearchStats stats;
FactorCache factor_cache;
bool valid_sq256[256] = {};
bool valid_sq63[63] = {};
atomic<u64> next_progress_checkpoint{PROGRESS_INTERVAL};

#define CUDA_CHECK(call)                                                       \
  do {                                                                         \
    cudaError_t status = (call);                                               \
    if (status != cudaSuccess) {                                               \
      cerr << "CUDA error: " << cudaGetErrorString(status) << " at "           \
           << __FILE__ << ':' << __LINE__ << "\n";                             \
      std::exit(1);                                                            \
    }                                                                          \
  } while (0)

void init_square_tables() {
  for (int i = 0; i < 256; ++i)
    valid_sq256[(i * i) & 255] = true;
  for (int i = 0; i < 63; ++i)
    valid_sq63[(i * i) % 63] = true;
}

u64 floor_sqrt_u128(u128 value) {
  if (value == 0)
    return 0;
  u64 root = static_cast<u64>(sqrtl(static_cast<long double>(value)));
  while ((u128)(root + 1) * (root + 1) <= value)
    ++root;
  while ((u128)root * root > value)
    --root;
  return root;
}

bool is_perfect_square(u128 value, u64 *root = nullptr) {
  if (!valid_sq256[static_cast<unsigned>(value & 255)])
    return false;
  if (!valid_sq63[static_cast<unsigned>(value % 63)])
    return false;

  u64 candidate = floor_sqrt_u128(value);
  if ((u128)candidate * candidate != value)
    return false;
  if (root)
    *root = candidate;
  return true;
}

inline u64 mulmod64(u64 a, u64 b, u64 m) {
  return static_cast<u128>(a) * b % m;
}

static u64 powmod64(u64 a, u64 b, u64 m) {
  u64 res = 1 % m;
  for (a %= m; b; b >>= 1, a = mulmod64(a, a, m)) {
    if (b & 1)
      res = mulmod64(res, a, m);
  }
  return res;
}

static bool is_prime64(u64 n) {
  if (n < 2)
    return false;
  if (n == 2 || n == 3 || n == 5 || n == 7)
    return true;
  if (n % 2 == 0 || n % 3 == 0 || n % 5 == 0)
    return false;

  u64 d = n - 1;
  int r = 0;
  while ((d & 1) == 0) {
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

static u64 pollard_rho(u64 n, u64 c) {
  auto f = [&](u64 x) { return (mulmod64(x, x, n) + c) % n; };
  u64 x = 2;
  u64 y = 2;
  u64 d = 1;

  while (d == 1) {
    x = f(x);
    y = f(f(y));
    u64 diff = x > y ? x - y : y - x;
    d = std::gcd(diff, n);
    if (x == y)
      return n;
  }
  return d;
}

static void factorize_impl(u64 n, vector<pair<u64, int>> &out) {
  if (n == 1)
    return;
  if (is_prime64(n)) {
    for (auto &[p, e] : out) {
      if (p == n) {
        ++e;
        return;
      }
    }
    out.push_back({n, 1});
    return;
  }

  u64 d = n;
  for (u64 c = 1; d == n || d <= 1; ++c)
    d = pollard_rho(n, c);
  factorize_impl(d, out);
  factorize_impl(n / d, out);
}

vector<pair<u64, int>> factorize_uncached(u64 n) {
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

vector<pair<u64, int>> factorize(u64 n) {
  if (n == 0)
    return {};

  {
    shared_lock<shared_mutex> lock(factor_cache.mutex);
    auto it = factor_cache.entries.find(n);
    if (it != factor_cache.entries.end()) {
      stats.factor_cache_hits.fetch_add(1, memory_order_relaxed);
      return it->second;
    }
  }

  stats.factor_cache_misses.fetch_add(1, memory_order_relaxed);
  vector<pair<u64, int>> factors = factorize_uncached(n);

  unique_lock<shared_mutex> lock(factor_cache.mutex);
  auto it = factor_cache.entries.find(n);
  if (it != factor_cache.entries.end()) {
    stats.factor_cache_hits.fetch_add(1, memory_order_relaxed);
    return it->second;
  }
  if (factor_cache.entries.size() >= FACTOR_CACHE_MAX_ENTRIES) {
    stats.factor_cache_skips.fetch_add(1, memory_order_relaxed);
    return factors;
  }

  auto [inserted_it, inserted] = factor_cache.entries.emplace(n, factors);
  if (inserted)
    stats.factor_cache_inserts.fetch_add(1, memory_order_relaxed);
  return inserted_it->second;
}

vector<pair<u64, int>> merge_factors(const vector<pair<u64, int>> &lhs,
                                     const vector<pair<u64, int>> &rhs) {
  vector<pair<u64, int>> merged = lhs;
  for (const auto &item : rhs) {
    auto it =
        find_if(merged.begin(), merged.end(),
                [&](const pair<u64, int> &v) { return v.first == item.first; });
    if (it != merged.end()) {
      it->second += item.second;
    } else {
      merged.push_back(item);
    }
  }
  return merged;
}

void get_divisors(const vector<pair<u64, int>> &factors, int idx, u128 current,
                  vector<u128> &divisors) {
  if (idx == static_cast<int>(factors.size())) {
    divisors.push_back(current);
    return;
  }

  u128 value = current;
  for (int i = 0; i <= factors[idx].second; ++i) {
    get_divisors(factors, idx + 1, value, divisors);
    value *= factors[idx].first;
  }
}

void log_progress(u64 checkpoint) {
  lock_guard<mutex> lock(io_mutex);
  progress_file << "k_values_checked=" << checkpoint << ", primitive_pairs="
                << stats.primitive_pairs.load(memory_order_relaxed)
                << ", tasks_emitted="
                << stats.tasks_emitted.load(memory_order_relaxed)
                << ", divisor_pairs_checked="
                << stats.divisor_pairs_checked.load(memory_order_relaxed)
                << ", square_hits="
                << stats.square_hits.load(memory_order_relaxed)
                << ", factor_cache_hits="
                << stats.factor_cache_hits.load(memory_order_relaxed)
                << ", factor_cache_misses="
                << stats.factor_cache_misses.load(memory_order_relaxed)
                << ", factor_cache_inserts="
                << stats.factor_cache_inserts.load(memory_order_relaxed)
                << ", factor_cache_skips="
                << stats.factor_cache_skips.load(memory_order_relaxed) << '\n';
  progress_file.flush();

  cout << "progress: k_values_checked=" << checkpoint << " primitive_pairs="
       << stats.primitive_pairs.load(memory_order_relaxed)
       << " tasks_emitted=" << stats.tasks_emitted.load(memory_order_relaxed)
       << " divisor_pairs_checked="
       << stats.divisor_pairs_checked.load(memory_order_relaxed)
       << " square_hits=" << stats.square_hits.load(memory_order_relaxed)
       << "\n"
       << flush;
}

void maybe_log_progress(u64 checked_count) {
  u64 expected = next_progress_checkpoint.load(memory_order_relaxed);
  while (checked_count >= expected) {
    if (next_progress_checkpoint.compare_exchange_weak(
            expected, expected + PROGRESS_INTERVAL, memory_order_relaxed,
            memory_order_relaxed)) {
      log_progress(expected);
      return;
    }
  }
}

__device__ __forceinline__ u64 gcd_u64_device(u64 a, u64 b) {
  while (b != 0) {
    u64 t = a % b;
    a = b;
    b = t;
  }
  return a;
}

__global__ void
generate_primitive_tasks_tile(u64 u_begin, u64 u_end, u64 v_begin, u64 v_end,
                              u64 edge_min, u64 edge_max, PrimitiveTask *tasks,
                              u64 capacity, unsigned long long *count) {
  u64 u_span = u_end - u_begin;
  u64 v_span = v_end - v_begin;
  u64 slot = static_cast<u64>(blockIdx.x) * blockDim.x + threadIdx.x;
  u64 total_slots = u_span * v_span;
  if (slot >= total_slots)
    return;

  u64 u = u_begin + slot / v_span;
  u64 v = v_begin + slot % v_span;
  if (v >= u)
    return;
  if (((u ^ v) & 1ULL) == 0)
    return;
  if (gcd_u64_device(u, v) != 1)
    return;

  u64 uu = u * u;
  u64 vv = v * v;
  u64 a_prime = uu - vv;
  u64 b_prime = 2 * u * v;
  u64 m_prime = uu + vv;
  u64 x = min(a_prime, b_prime);
  u64 y = max(a_prime, b_prime);
  u64 k_min = (edge_min + y - 1) / y;
  u64 k_max = edge_max / y;

  if (k_min > k_max)
    return;

  unsigned long long index = atomicAdd(count, 1ULL);
  if (index >= capacity)
    return;

  tasks[index] = PrimitiveTask{u, v, x, y, m_prime, k_min, k_max};
}

u64 estimate_tile_capacity(u64 u_begin, u64 u_end, u64 v_begin, u64 v_end) {
  if (u_begin >= u_end || v_begin >= v_end)
    return 0;
  return (u_end - u_begin) * (v_end - v_begin);
}

void process_task_range(const PrimitiveTask *tasks, size_t begin, size_t end,
                        bool primitive_only) {
  for (size_t idx = begin; idx < end; ++idx) {
    const PrimitiveTask &task = tasks[idx];
    stats.primitive_pairs.fetch_add(1, memory_order_relaxed);

    auto factors_y_minus_x = factorize(task.y - task.x);
    auto factors_y_plus_x = factorize(task.y + task.x);
    auto base_factors = merge_factors(factors_y_minus_x, factors_y_plus_x);

    for (u64 k = task.k_min; k <= task.k_max; ++k) {
      if (primitive_only && (k & 3ULL) == 2ULL)
        continue;

      u64 checked_count =
          stats.k_values_checked.fetch_add(1, memory_order_relaxed) + 1;
      maybe_log_progress(checked_count);

      u64 a = k * task.x;
      u64 b = k * task.y;
      u64 m = k * task.m;

      auto factors_k = factorize(k);
      auto factors_k2 = factors_k;
      for (auto &item : factors_k2)
        item.second *= 2;
      auto total_factors = merge_factors(base_factors, factors_k2);

      vector<u128> divisors;
      get_divisors(total_factors, 0, 1, divisors);

      u128 diff = (u128)b * b - (u128)a * a;
      for (u128 d1 : divisors) {
        u128 d2 = diff / d1;
        if (d1 >= d2)
          continue;
        if ((d1 & 1) != (d2 & 1))
          continue;

        stats.divisor_pairs_checked.fetch_add(1, memory_order_relaxed);

        u128 n = (d1 + d2) / 2;
        if (n <= b)
          continue;

        u128 c2 = n * n - (u128)b * b;
        if (c2 == 0)
          continue;

        if (primitive_only) {
          if ((k & 1ULL) && (c2 & 15ULL))
            continue;
          if ((k & 3ULL) == 0ULL && (c2 & 3ULL) != 1ULL)
            continue;
        }

        u64 c = 0;
        if (!is_perfect_square(c2, &c))
          continue;
        if (std::gcd(std::gcd(a, b), c) != 1)
          continue;

        stats.square_hits.fetch_add(1, memory_order_relaxed);

        u128 p2 = (u128)m * m + c2;
        u64 p = 0;
        {
          lock_guard<mutex> lock(io_mutex);
          euler_result_file << task.u << ',' << task.v << ',' << k << ',' << a
                            << ',' << b << ',' << c << '\n';
        }
        if (!is_perfect_square(p2, &p))
          continue;

        lock_guard<mutex> lock(io_mutex);
        cout << "FOUND cuboid: u=" << task.u << " v=" << task.v << " k=" << k
             << " a=" << a << " b=" << b << " c=" << c << "\n";
        result_file << task.u << ',' << task.v << ',' << k << ',' << a << ','
                    << b << ',' << c << '\n';
        result_file.flush();
      }
    }
  }
}

void init_pipeline_slot(PipelineSlot *slot, u64 capacity) {
  slot->capacity = capacity;
  CUDA_CHECK(cudaStreamCreate(&slot->stream));
  CUDA_CHECK(cudaMalloc(&slot->device_tasks, capacity * sizeof(PrimitiveTask)));
  CUDA_CHECK(cudaMalloc(&slot->device_count, sizeof(unsigned long long)));
  CUDA_CHECK(cudaHostAlloc(&slot->host_tasks, capacity * sizeof(PrimitiveTask),
                           cudaHostAllocDefault));
  CUDA_CHECK(cudaHostAlloc(&slot->host_count, sizeof(unsigned long long),
                           cudaHostAllocDefault));
  *slot->host_count = 0;
}

void destroy_pipeline_slot(PipelineSlot *slot) {
  if (slot->stream)
    CUDA_CHECK(cudaStreamSynchronize(slot->stream));
  if (slot->device_tasks)
    CUDA_CHECK(cudaFree(slot->device_tasks));
  if (slot->device_count)
    CUDA_CHECK(cudaFree(slot->device_count));
  if (slot->host_tasks)
    CUDA_CHECK(cudaFreeHost(slot->host_tasks));
  if (slot->host_count)
    CUDA_CHECK(cudaFreeHost(slot->host_count));
  if (slot->stream)
    CUDA_CHECK(cudaStreamDestroy(slot->stream));
  *slot = PipelineSlot{};
}

void launch_tile(PipelineSlot *slot, const TileWindow &tile, u64 edge_min,
                 u64 edge_max) {
  slot->tile = tile;
  slot->active = true;
  *slot->host_count = 0;

  CUDA_CHECK(cudaMemsetAsync(slot->device_count, 0, sizeof(unsigned long long),
                             slot->stream));

  u64 total_slots = estimate_tile_capacity(tile.u_begin, tile.u_end,
                                           tile.v_begin, tile.v_end);
  int blocks =
      static_cast<int>((total_slots + CUDA_THREADS - 1) / CUDA_THREADS);
  generate_primitive_tasks_tile<<<blocks, CUDA_THREADS, 0, slot->stream>>>(
      tile.u_begin, tile.u_end, tile.v_begin, tile.v_end, edge_min, edge_max,
      slot->device_tasks, slot->capacity, slot->device_count);
  CUDA_CHECK(cudaGetLastError());

  CUDA_CHECK(cudaMemcpyAsync(slot->host_count, slot->device_count,
                             sizeof(unsigned long long), cudaMemcpyDeviceToHost,
                             slot->stream));
  CUDA_CHECK(cudaMemcpyAsync(slot->host_tasks, slot->device_tasks,
                             slot->capacity * sizeof(PrimitiveTask),
                             cudaMemcpyDeviceToHost, slot->stream));
}

void process_task_batch(const PrimitiveTask *tasks, size_t task_count,
                        bool primitive_only) {
  if (task_count == 0)
    return;

  int workers = static_cast<int>(thread::hardware_concurrency());
  if (workers <= 0)
    workers = 8;
  workers = min<int>(workers, static_cast<int>(task_count));

  vector<thread> cpu_workers;
  size_t chunk = (task_count + workers - 1) / workers;
  for (int i = 0; i < workers; ++i) {
    size_t begin = static_cast<size_t>(i) * chunk;
    size_t end = min(task_count, begin + chunk);
    if (begin < end) {
      cpu_workers.emplace_back(process_task_range, tasks, begin, end,
                               primitive_only);
    }
  }
  for (auto &worker : cpu_workers)
    worker.join();
}

u64 finalize_tile(PipelineSlot *slot, bool primitive_only) {
  if (!slot->active)
    return 0;

  CUDA_CHECK(cudaStreamSynchronize(slot->stream));
  u64 task_count = min<u64>(*slot->host_count, slot->capacity);
  stats.tasks_emitted.fetch_add(task_count, memory_order_relaxed);
  process_task_batch(slot->host_tasks, static_cast<size_t>(task_count),
                     primitive_only);
  slot->active = false;
  return task_count;
}

bool parse_u64_arg(const string &text, u64 *value) {
  try {
    size_t parsed = 0;
    unsigned long long temp = stoull(text, &parsed, 10);
    if (parsed != text.size())
      return false;
    *value = static_cast<u64>(temp);
    return true;
  } catch (...) {
    return false;
  }
}

vector<u64> extract_numbers(const string &text) {
  vector<u64> numbers;
  u64 value = 0;
  bool in_number = false;

  for (char ch : text) {
    if (ch >= '0' && ch <= '9') {
      value = value * 10 + static_cast<u64>(ch - '0');
      in_number = true;
    } else if (in_number) {
      numbers.push_back(value);
      value = 0;
      in_number = false;
    }
  }
  if (in_number)
    numbers.push_back(value);
  return numbers;
}

bool parse_candidate_arg(const string &text, CandidateTriplet *candidate) {
  vector<u64> numbers = extract_numbers(text);
  if (numbers.size() < 4)
    return false;
  candidate->a = numbers[numbers.size() - 3];
  candidate->b = numbers[numbers.size() - 2];
  candidate->c = numbers[numbers.size() - 1];
  return true;
}

bool validate_candidate(const CandidateTriplet &candidate) {
  u128 a2 = (u128)candidate.a * candidate.a;
  u128 b2 = (u128)candidate.b * candidate.b;
  u128 c2 = (u128)candidate.c * candidate.c;

  u64 root_ab = 0;
  u64 root_bc = 0;
  u64 root_ac = 0;
  u64 root_space = 0;

  bool ok_ab = is_perfect_square(a2 + b2, &root_ab);
  bool ok_bc = is_perfect_square(b2 + c2, &root_bc);
  bool ok_ac = is_perfect_square(a2 + c2, &root_ac);
  bool ok_space = is_perfect_square(a2 + b2 + c2, &root_space);

  cout << "candidate a=" << candidate.a << " b=" << candidate.b
       << " c=" << candidate.c << " -> faces=" << ok_ab << ok_bc << ok_ac
       << " space=" << ok_space;
  if (ok_ab)
    cout << " roots(ab,bc,ac)=(" << root_ab << ',' << root_bc << ',' << root_ac
         << ')';
  cout << "\n";
  return ok_ab && ok_bc && ok_ac && ok_space;
}

int run_candidate_validation(const vector<string> &candidate_args) {
  bool all_valid = true;
  for (const string &arg : candidate_args) {
    CandidateTriplet candidate{};
    if (!parse_candidate_arg(arg, &candidate)) {
      cerr << "Failed to parse candidate: " << arg << "\n";
      return 1;
    }
    all_valid = validate_candidate(candidate) && all_valid;
  }
  return all_valid ? 0 : 2;
}

int main(int argc, char **argv) {
  bool primitive_only = true;
  vector<string> candidate_args;
  bool validate_only = false;

  init_square_tables();

  result_file.open(OUTPUT_FILE, ios::app);
  if (!result_file.is_open()) {
    cerr << "Failed to open output file: " << OUTPUT_FILE << "\n";
    return 1;
  }
  euler_result_file.open(EULER_OUTPUT_FILE, ios::app);
  if (!euler_result_file.is_open()) {
    cerr << "Failed to open output file: " << EULER_OUTPUT_FILE << "\n";
    return 1;
  }
  progress_file.open(PROGRESS_FILE, ios::app);
  if (!progress_file.is_open()) {
    cerr << "Failed to open output file: " << PROGRESS_FILE << "\n";
    return 1;
  }

  u64 search_edge_min = DEFAULT_EDGE_MIN;
  u64 search_edge_max = DEFAULT_EDGE_MAX;

  const long double max_m =
      sqrtl(2.0L) * static_cast<long double>(search_edge_max);
  const u64 default_u_end = static_cast<u64>(ceill(sqrtl(max_m)));
  u64 user_u_begin = 2;
  u64 user_u_end = default_u_end;

  for (int i = 1; i < argc; ++i) {
    string arg = argv[i];
    if (arg == "--all") {
      primitive_only = false;
      continue;
    }
    if (arg == "--primitive-only") {
      primitive_only = true;
      continue;
    }
    if (arg == "--validate-candidates") {
      validate_only = true;
      continue;
    }
    if (arg.rfind("--candidate=", 0) == 0) {
      candidate_args.push_back(arg.substr(12));
      continue;
    }
    if (arg.rfind("--u-start=", 0) == 0) {
      if (!parse_u64_arg(arg.substr(10), &user_u_begin)) {
        cerr << "Invalid --u-start value\n";
        return 1;
      }
      continue;
    }
    if (arg.rfind("--u-end=", 0) == 0) {
      if (!parse_u64_arg(arg.substr(8), &user_u_end)) {
        cerr << "Invalid --u-end value\n";
        return 1;
      }
      continue;
    }
    if (arg.rfind("--edge-min=", 0) == 0) {
      if (!parse_u64_arg(arg.substr(11), &search_edge_min)) {
        cerr << "Invalid --edge-min value\n";
        return 1;
      }
      continue;
    }
    if (arg.rfind("--edge-max=", 0) == 0) {
      if (!parse_u64_arg(arg.substr(11), &search_edge_max)) {
        cerr << "Invalid --edge-max value\n";
        return 1;
      }
      continue;
    }
    cerr << "Unknown argument: " << arg << "\n";
    return 1;
  }

  if (validate_only) {
    result_file.close();
    euler_result_file.close();
    progress_file.close();
    if (candidate_args.empty()) {
      cerr << "No candidates provided\n";
      return 1;
    }
    return run_candidate_validation(candidate_args);
  }

  if (search_edge_min == 0 || search_edge_min > search_edge_max) {
    cerr << "Invalid edge range\n";
    return 1;
  }

  const long double runtime_max_m =
      sqrtl(2.0L) * static_cast<long double>(search_edge_max);
  user_u_end =
      min<u64>(user_u_end, static_cast<u64>(ceill(sqrtl(runtime_max_m))));
  user_u_begin = max<u64>(2, user_u_begin);
  if (user_u_begin >= user_u_end) {
    cerr << "Invalid u range\n";
    return 1;
  }

  cout << "CUDA hybrid search start, u_range=[" << user_u_begin << ", "
       << user_u_end << ")"
       << ", primitive_only=" << (primitive_only ? "true" : "false")
       << ", edge_range=[" << search_edge_min << ", " << search_edge_max << "]"
       << ", u_batch=" << U_BATCH << ", v_tile=" << V_TILE << "\n";

  PipelineSlot slots[PIPELINE_SLOTS];
  const u64 tile_capacity = U_BATCH * V_TILE;
  for (auto &slot : slots)
    init_pipeline_slot(&slot, tile_capacity);

  u64 next_u_begin = user_u_begin;
  u64 next_v_begin = 1;
  auto next_tile = [&](TileWindow *tile) {
    while (next_u_begin < user_u_end) {
      u64 u_stop = min(user_u_end, next_u_begin + U_BATCH);
      if (next_v_begin >= u_stop) {
        next_u_begin += U_BATCH;
        next_v_begin = 1;
        continue;
      }

      tile->u_begin = next_u_begin;
      tile->u_end = u_stop;
      tile->v_begin = next_v_begin;
      tile->v_end = min(u_stop, next_v_begin + V_TILE);
      next_v_begin += V_TILE;
      return true;
    }
    return false;
  };

  bool have_batch = false;
  u64 batch_u_begin = 0;
  u64 batch_u_end = 0;
  u64 batch_tasks = 0;
  auto record_tile = [&](const TileWindow &tile, u64 task_count) {
    if (!have_batch || tile.u_begin != batch_u_begin) {
      if (have_batch) {
        cout << "u batch [" << batch_u_begin << ", " << batch_u_end
             << ") -> tasks=" << batch_tasks << "\n";
      }
      have_batch = true;
      batch_u_begin = tile.u_begin;
      batch_u_end = tile.u_end;
      batch_tasks = 0;
    }

    batch_tasks += task_count;
    cout << "tile u=[" << tile.u_begin << ", " << tile.u_end << ") v=["
         << tile.v_begin << ", " << tile.v_end << ") -> tasks=" << task_count
         << "\n";
  };

  TileWindow first_tile{};
  bool has_first_tile = next_tile(&first_tile);
  if (has_first_tile)
    launch_tile(&slots[0], first_tile, search_edge_min, search_edge_max);

  size_t submitted = has_first_tile ? 1 : 0;
  size_t completed = 0;

  while (completed < submitted) {
    size_t launch_index = submitted % PIPELINE_SLOTS;
    TileWindow tile{};
    bool has_next = next_tile(&tile);
    if (has_next) {
      launch_tile(&slots[launch_index], tile, search_edge_min, search_edge_max);
      ++submitted;
    }

    size_t finalize_index = completed % PIPELINE_SLOTS;
    PipelineSlot &slot = slots[finalize_index];
    u64 task_count = finalize_tile(&slot, primitive_only);
    record_tile(slot.tile, task_count);
    ++completed;
  }

  if (have_batch) {
    cout << "u batch [" << batch_u_begin << ", " << batch_u_end
         << ") -> tasks=" << batch_tasks << "\n";
  }

  for (auto &slot : slots)
    destroy_pipeline_slot(&slot);

  result_file.close();
  euler_result_file.close();
  progress_file.close();
  cout << "primitive_pairs=" << stats.primitive_pairs.load()
       << " tasks_emitted=" << stats.tasks_emitted.load()
       << " k_values_checked=" << stats.k_values_checked.load()
       << " divisor_pairs_checked=" << stats.divisor_pairs_checked.load()
       << " square_hits=" << stats.square_hits.load()
       << " factor_cache_hits=" << stats.factor_cache_hits.load()
       << " factor_cache_misses=" << stats.factor_cache_misses.load()
       << " factor_cache_inserts=" << stats.factor_cache_inserts.load()
       << " factor_cache_skips=" << stats.factor_cache_skips.load() << "\n";
  return 0;
}
