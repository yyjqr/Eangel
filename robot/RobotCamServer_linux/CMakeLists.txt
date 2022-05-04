cmake_minimum_required(VERSION 3.5)

project(robotCamServer LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
#set(CMAKE_CXX_STANDARD 14)
## It prevents the decay to C++98 when the compiler does not support C++14
#set(CMAKE_CXX_STANDARD_REQUIRED ON)
# It disables the use of compiler-specific extensions
# e.g. -std=c++14 rather than -std=gnu++14
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -g -Wall -pthread -no-pie")
add_definitions(-DQT_NO_DEBUG)
option (IN_TEST "option for indoor test" OFF)
if (IN_TEST)
     add_definitions(-DIN_TEST)
endif(IN_TEST)

# Try to find OpenCV
# set(OpenCV_DIR ....)
#find_package(OpenCV 4.1 REQUIRED)
find_package(OpenCV  REQUIRED)
if (OpenCV_FOUND)
    # If the package has been found, several variables will
    # be set, you can find the full list with descriptions
    # in the OpenCVConfig.cmake file.
    # Print some message showing some of them
    message(STATUS "OpenCV library status:")
    message(STATUS "    version: ${OpenCV_VERSION}")
    message(STATUS "    include path: ${OpenCV_INCLUDE_DIRS}" \n)
else ()
    message(FATAL_ERROR "Could not locate OpenCV" \n)
endif()

file(GLOB SOURCE_FILES src/*.cpp)
add_executable(${CMAKE_PROJECT_NAME} ${SOURCE_FILES})

target_link_libraries(${CMAKE_PROJECT_NAME} ${OpenCV_LIBS})
