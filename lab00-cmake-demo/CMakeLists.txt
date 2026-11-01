cmake_minimum_required(VERSION 3.20)

project(MyFirstProject LANGUAGES CXX)

add_executable(my_program main.cpp)

target_compile_features(my_program PRIVATE cxx_std_17)