
set (CMAKE_CXX_STANDARD 17)
add_library(carp INTERFACE)

target_include_directories(carp INTERFACE "${CMAKE_CURRENT_LIST_DIR}/inc")