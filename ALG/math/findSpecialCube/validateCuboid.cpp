#include <iostream>
#include <vector>
#include <cmath>
#include <iomanip>

using namespace std;

using u64 = uint64_t;
using u128 = __uint128_t;

// 辅助函数：输出 u128 类型
ostream& operator<<(ostream& os, u128 v) {
    if (v == 0) return os << "0";
    string s;
    while (v > 0) {
        s += (char)('0' + (v % 10));
        v /= 10;
    }
    for (int i = 0; i < s.length() / 2; ++i) {
        swap(s[i], s[s.length() - 1 - i]);
    }
    return os << s;
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

void check_cuboid(u64 a, u64 b, u64 c) {
    cout << "----------------------------------------\n";
    cout << "Checking a=" << a << " b=" << b << " c=" << c << "\n";
    
    u128 a2 = (u128)a * a;
    u128 b2 = (u128)b * b;
    u128 c2 = (u128)c * c;
    
    u128 face_ab = a2 + b2;
    u128 face_bc = b2 + c2;
    u128 face_ac = a2 + c2;
    u128 space_diag = a2 + b2 + c2;
    
    u64 root_ab, root_bc, root_ac, root_space;
    bool ok_ab = is_perfect_square(face_ab, &root_ab);
    bool ok_bc = is_perfect_square(face_bc, &root_bc);
    bool ok_ac = is_perfect_square(face_ac, &root_ac);
    bool ok_space = is_perfect_square(space_diag, &root_space);
    
    cout << "  [Face AB] a^2 + b^2 = " << face_ab << " -> " 
         << (ok_ab ? "Valid Square (root=" + to_string(root_ab) + ")" : "NOT a square") << "\n";
         
    cout << "  [Face BC] b^2 + c^2 = " << face_bc << " -> " 
         << (ok_bc ? "Valid Square (root=" + to_string(root_bc) + ")" : "NOT a square") << "\n";
         
    cout << "  [Face AC] a^2 + c^2 = " << face_ac << " -> " 
         << (ok_ac ? "Valid Square (root=" + to_string(root_ac) + ")" : "NOT a square") << "\n";
         
    cout << "  [Space  ] a^2+b^2+c^2 = " << space_diag << " -> " 
         << (ok_space ? "Valid Square (root=" + to_string(root_space) + ")" : "NOT a square") << "\n";
         
    if (ok_ab && ok_bc && ok_ac && ok_space) {
        cout << "  >>> PERFECT CUBOID FOUND! <<<\n";
    } else {
        cout << "  >>> FAILED <<<\n";
    }
}

int main() {
    struct TestData {
        u64 a, b, c;
    };
    vector<TestData> tests = {
        // Original tests
        {1529962181632ULL, 3334013810820ULL, 1856954875776ULL},
        {1912452727040ULL, 4167517263525ULL, 2321193594720ULL},
        {2294943272448ULL, 5001020716230ULL, 2785432313664ULL},
        {2677433817856ULL, 5834524168935ULL, 3249671032608ULL},
        {3059924363264ULL, 6668027621640ULL, 3713909751552ULL},
        {3442414908672ULL, 7501531074345ULL, 4178148470496ULL},
        {3824905454080ULL, 8335034527050ULL, 4642387189440ULL},
        {2280290088384ULL, 5562075657425ULL, 1495296615888ULL},

        // Newly added from comments
        {1622090280096ULL, 3137983798760ULL, 41973899721600ULL},
        {1824851565108ULL, 3530231773605ULL, 47220637186800ULL},
        {2027612850120ULL, 3922479748450ULL, 52467374652000ULL},
        {2749943218498ULL, 3531644173200ULL, 21735419022720ULL},
        {4124914827747ULL, 5297466259800ULL, 32603128534080ULL},
        {5499886436996ULL, 7063288346400ULL, 43470838045440ULL},
        {6874858046245ULL, 8829110433000ULL, 54338547556800ULL},
        {4025046630ULL, 3030613536160ULL, 4396934325672ULL},
        {2304979927146ULL, 3546027333120ULL, 5674676765472ULL},
        {2689143248337ULL, 4137031888640ULL, 6620456226384ULL},
        {3073306569528ULL, 4728036444160ULL, 7566235687296ULL},
        {3457469890719ULL, 5319040999680ULL, 8512015148208ULL},
        {3841633211910ULL, 5910045555200ULL, 9457794609120ULL},
        {3613780015680ULL, 4921040000578ULL, 8747588401200ULL},
        {5420670023520ULL, 7381560000867ULL, 13121382601800ULL},
        {7227560031360ULL, 9842080001156ULL, 17495176802400ULL},
        {270245079104ULL, 3281091529905ULL, 2772351027600ULL},
        {308851518976ULL, 3749818891320ULL, 3168401174400ULL},
        {347457958848ULL, 4218546252735ULL, 3564451321200ULL},
        {386064398720ULL, 4687273614150ULL, 456909177816ULL},
        {386064398720ULL, 4687273614150ULL, 3960501468000ULL},
        {152745095802ULL, 3444383580440ULL, 851342019264ULL},
        {229117643703ULL, 5166575370660ULL, 1277013028896ULL},
        {305490191604ULL, 6888767160880ULL, 1702684038528ULL},
        {381862739505ULL, 8610958951100ULL, 2128355048160ULL},
        {1773152238297ULL, 3336844748580ULL, 1573977475440ULL},
        {2364202984396ULL, 4449126331440ULL, 5012129103597ULL},
        {2364202984396ULL, 4449126331440ULL, 2098636633920ULL},
        {2955253730495ULL, 5561407914300ULL, 2623295792400ULL},
        {3546304476594ULL, 6673689497160ULL, 3147954950880ULL},
        {4137355222693ULL, 7785971080020ULL, 3672614109360ULL},
        {4728405968792ULL, 8898252662880ULL, 10024258207194ULL},
        {4728405968792ULL, 8898252662880ULL, 4197273267840ULL},
        {1584030139488ULL, 5762047021016ULL, 7652737219050ULL},
        {476706562570ULL, 5340302922240ULL, 35179543237608ULL},
        {1985172121881ULL, 5814953872200ULL, 6052494041920ULL}
    };
    
    for (const auto& t : tests) {
        check_cuboid(t.a, t.b, t.c);
    }
    
    return 0;
}
