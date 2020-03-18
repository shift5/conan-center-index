cmake_minimum_required(VERSION 2.8.12)
project(test_package)

include(${CMAKE_BINARY_DIR}/conanbuildinfo.cmake)
conan_basic_setup(TARGETS)

set(CMAKE_VERBOSE_MAKEFILE ON)

find_package(protoc CONFIG REQUIRED)

add_executable(${PROJECT_NAME} test_package.cpp addressbook.proto)
PROTOBUF_GENERATE(TARGET ${PROJECT_NAME})
conan_target_link_libraries(${PROJECT_NAME})
target_include_directories(${PROJECT_NAME} PUBLIC ${CMAKE_CURRENT_BINARY_DIR})