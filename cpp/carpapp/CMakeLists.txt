set (CMAKE_CXX_STANDARD 17)
add_executable(carpapp ${CMAKE_CURRENT_LIST_DIR}/main.cpp)
target_link_libraries(carpapp carp)