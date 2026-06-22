
1. vector  索引访问   vector<int> vec_data {10, 20,30};
vec_data[1], vec_data.at(i);
sort进行排序，通用的sort算法。
transform函数，  transform(v.begin(),v.end(),v.begin(),[](x){return x+1;});

2.list 容器
随机指针，需要按指针访问
for(auto it : lis_obj)
{
    cout << "ele:"<<*it<<endl;
}

list里面，需要单独编写sort函数，不能采用通用的sort函数。

##2 智能指针
https://cloud.tencent.com/developer/article/2574907
特性

unique_ptr

shared_ptr

内存占用

小（指针+删除器）

控制块额外开销，atomic计数

拷贝/移动开销

禁止拷贝，移动开销小

拷贝需要原子操作，移动开销小

多线程安全

依赖外部保护

引用计数原子操作保证安全

循环引用风险

无

有，需要 weak_ptr

适用场景

独占资源，RAII

多方共享对象管理，缓存，异步任务
