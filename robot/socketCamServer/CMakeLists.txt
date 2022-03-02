cmake_minimum_required(VERSION 3.5)

project(socketCamServer LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Try to find OpenCV
# set(OpenCV_DIR ....)
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

add_executable(${CMAKE_PROJECT_NAME} main.cpp tcpsocket.cpp)

target_link_libraries(${CMAKE_PROJECT_NAME} ${OpenCV_LIBS})
