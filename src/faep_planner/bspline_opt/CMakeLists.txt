cmake_minimum_required(VERSION 2.8.3)
project(bspline_opt)

set(CMAKE_BUILD_TYPE "Release")
set(CMAKE_CXX_FLAGS "-std=c++14")
set(CMAKE_CXX_FLAGS_RELEASE "-O3 -Wall")

find_package(Eigen3 REQUIRED)
find_package(PCL 1.7 REQUIRED)

find_package(catkin REQUIRED COMPONENTS
  roscpp
  rospy
  std_msgs
  visualization_msgs
  plan_env
  active_perception
  cv_bridge
)

catkin_package(
 INCLUDE_DIRS include
 LIBRARIES bspline_opt
 CATKIN_DEPENDS plan_env active_perception
#  DEPENDS system_lib
)

include_directories( 
    SYSTEM 
    include 
    ${catkin_INCLUDE_DIRS}
    ${Eigen3_INCLUDE_DIRS} 
    ${PCL_INCLUDE_DIRS}
)

add_library( bspline_opt 
    src/bspline_optimizer.cpp 
    )
target_link_libraries( bspline_opt
    ${catkin_LIBRARIES} 
    # 用系统的现代 nlopt（ROS 自带的 2.1.21 版 nlopt C++ 封装在运行期会崩溃）
    # 注意：ROS 自带了同名 SONAME 的旧 libnlopt_cxx.so.0，会被 LD_LIBRARY_PATH 优先加载；
    # 因此这里链接系统 C 版 libnlopt.so（ROS 中没有该 SONAME，运行时必然解析到 /usr 的新版）
    /usr/lib/x86_64-linux-gnu/libnlopt.so
    # /usr/local/lib/libnlopt.so
    )  
