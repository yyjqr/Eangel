cmake_minimum_required(VERSION 2.8)

project(getBoostTime)

find_package(Boost REQUIRED COMPONENTS thread system filesystem iostreams program_options random timer chrono)#for boost)
if(NOT Boost_FOUND)
    message("NOT found Boost")
endif()

include_directories(${Boost_INCLUDE_DIRS})

add_executable(${PROJECT_NAME} "main.cpp"  )

target_link_libraries(
   ${PROJECT_NAME}
   ${Boost_LIBRARIES}

   )
