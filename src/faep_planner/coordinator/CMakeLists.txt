cmake_minimum_required(VERSION 3.0.2)
project(coordinator)

set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11")

find_package(Eigen3 REQUIRED)

find_package(catkin REQUIRED COMPONENTS
  coord_msgs
  geometry_msgs
  roscpp
  std_msgs
)

catkin_package(
  CATKIN_DEPENDS coord_msgs geometry_msgs roscpp std_msgs
)

include_directories(
  ${catkin_INCLUDE_DIRS}
  ${EIGEN3_INCLUDE_DIR}
)

add_executable(faep_coordinator src/coordinator.cpp)
target_link_libraries(faep_coordinator ${catkin_LIBRARIES})
add_dependencies(faep_coordinator ${${PROJECT_NAME}_EXPORTED_TARGETS} ${catkin_EXPORTED_TARGETS})
