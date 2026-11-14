cmake_minimum_required(VERSION 3.0.2)
project(target_search)

set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11")

find_package(Eigen3 REQUIRED)
find_package(catkin REQUIRED COMPONENTS
  coord_msgs
  cv_bridge
  geometry_msgs
  roscpp
  sensor_msgs
  std_msgs
)

catkin_package(
  CATKIN_DEPENDS coord_msgs cv_bridge geometry_msgs roscpp sensor_msgs std_msgs
)

include_directories(
  ${catkin_INCLUDE_DIRS}
  ${EIGEN3_INCLUDE_DIR}
)

add_executable(target_perception_sim src/target_perception_sim.cpp)
target_link_libraries(target_perception_sim ${catkin_LIBRARIES})
add_dependencies(target_perception_sim ${${PROJECT_NAME}_EXPORTED_TARGETS} ${catkin_EXPORTED_TARGETS})
