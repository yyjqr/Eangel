cmake_minimum_required(VERSION 3.2)
project( videoRecord VERSION 1.0.0 LANGUAGES CXX)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
#设置使能 moc ，uic，rcc
#set(CMAKE_AUTOMOC ON)
#set(CMAKE_AUTORCC ON)
#set(CMAKE_AUTOUIC ON)

set(CMAKE_CXX_STANDARD 14)
# It prevents the decay to C++98 when the compiler does not support C++14
set(CMAKE_CXX_STANDARD_REQUIRED ON)
# It disables the use of compiler-specific extensions
# e.g. -std=c++14 rather than -std=gnu++14
set(CMAKE_CXX_EXTENSIONS OFF)
SET(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11 -pthread")

find_package( OpenCV REQUIRED )
include_directories( ${OpenCV_INCLUDE_DIRS} )
include_directories(../include )
#file(GLOB SOURCE_FILES video_record_v1.4/*.cpp video_record_v1.4/*.c)
file(GLOB SOURCE_FILES src/*.cpp )
add_executable( videoRecord ${SOURCE_FILES} )
target_link_libraries( videoRecord ${OpenCV_LIBS} )
