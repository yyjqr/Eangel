cmake_minimum_required(VERSION 2.8)

project(testEigen)

#find_package(Boost REQUIRED COMPONENTS thread system filesystem iostreams program_options random timer chrono)#for boost)
#if(NOT Boost_FOUND)
#    message("NOT found Boost")
#endif()


#include_directories(${Boost_INCLUDE_DIRS})

find_package(Eigen3 REQUIRED)

INCLUDE_DIRECTORIES(${EIGEN3_INCLUDE_DIR})

add_executable(${PROJECT_NAME} "eigenTest.cpp"  )

target_link_libraries(
   ${PROJECT_NAME}
   
    Eigen3::Eigen
   )
