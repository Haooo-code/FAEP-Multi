
#include <plan_manage/planner_manager.h>
#include <exploration_manager/fast_exploration_manager.h>
#include <traj_utils/planning_visualization.h>

#include "visualization_msgs/Marker.h"

#include <exploration_manager/fast_exploration_fsm.h>
#include <exploration_manager/expl_data.h>
#include <plan_env/edt_environment.h>
#include <plan_env/sdf_map.h>

#include <fstream>
#include <malloc.h>

using Eigen::Vector4d;
using namespace termcolor;

namespace fast_planner
{
  void FastExplorationFSM::init(ros::NodeHandle &nh)
  {
    fp_.reset(new FSMParam);
    fd_.reset(new FSMData);

    /*  Fsm param  */
    nh.param("fsm/thresh_replan1", fp_->replan_thresh1_, -1.0);
    nh.param("fsm/thresh_replan2", fp_->replan_thresh2_, -1.0);
    nh.param("fsm/thresh_replan3", fp_->replan_thresh3_, -1.0);
    nh.param("fsm/init_x", fp_->init_x, 0.0);
    nh.param("fsm/init_y", fp_->init_y, 0.0);
    nh.param("fsm/init_z", fp_->init_z, 0.0);
    nh.param("fsm/replan_time", fp_->replan_time_, -1.0);
    // 调试输出文件路径（原代码写死为作者服务器路径；多机时每机需独立文件；留空则关闭写文件）
    nh.param("fsm/path_file", fp_->path_file_, string(""));
    nh.param("fsm/result_file", fp_->result_file_, string(""));

    /* Initialize main modules */
    expl_manager_.reset(new FastExplorationManager);
    expl_manager_->initialize(nh);
    visualization_.reset(new PlanningVisualization(nh));

    planner_manager_ = expl_manager_->planner_manager_;
    state_ = EXPL_STATE::INIT;
    fd_->have_odom_ = false;
    fd_->state_str_ = {"INIT", "WAIT_TRIGGER", "YAWING", "PLAN_TRAJ", "PUB_TRAJ", "EXEC_TRAJ", "FINISH"};
    fd_->static_state_ = true;
    fd_->trigger_ = false;

    /* Ros sub, pub and timer */
    exec_timer_ = nh.createTimer(ros::Duration(0.01), &FastExplorationFSM::FSMCallback, this);
    safety_timer_ = nh.createTimer(ros::Duration(0.05), &FastExplorationFSM::safetyCallback, this);
    frontier_timer_ = nh.createTimer(ros::Duration(0.5), &FastExplorationFSM::frontierCallback, this);

    trigger_sub_ =
        nh.subscribe("/waypoint_generator/waypoints", 1, &FastExplorationFSM::triggerCallback, this);
    odom_sub_ = nh.subscribe("/odom_world", 1, &FastExplorationFSM::odometryCallback, this);

    pg_T_vio_sub = nh.subscribe("/loop_fusion/pg_T_vio", 10, &FastExplorationFSM::pgTVioCallback, this);

    //traj_server
    cmd_vis_pub = nh.advertise<visualization_msgs::Marker>("/planning/position_cmd_vis", 10);
    pos_cmd_pub = nh.advertise<quadrotor_msgs::PositionCommand>("/planning/pos_cmd", 50);
    traj_pub = nh.advertise<visualization_msgs::Marker>("/planning/travel_traj", 10);
    vis_timer = nh.createTimer(ros::Duration(0.25), &FastExplorationFSM::visCallback, this);
    vis_all_timer_ = nh.createTimer(ros::Duration(0.1), &FastExplorationFSM::visualize, this);

    traj_cmd_.clear();

    /* control parameter */
    cmd.kx[0] = pos_gain[0];
    cmd.kx[1] = pos_gain[1];
    cmd.kx[2] = pos_gain[2];

    cmd.kv[0] = vel_gain[0];
    cmd.kv[1] = vel_gain[1];
    cmd.kv[2] = vel_gain[2];
    last_yaw_ = 0.0;

    cmd.header.stamp = ros::Time::now();
    cmd.header.frame_id = "world";
    cmd.trajectory_flag = quadrotor_msgs::PositionCommand::TRAJECTORY_STATUS_READY;
    cmd.trajectory_id = traj_id_;
    cmd.position.x = fp_->init_x;
    cmd.position.y = fp_->init_y;
    cmd.position.z = fp_->init_z;
    cmd.velocity.x = 0.0;
    cmd.velocity.y = 0.0;
    cmd.velocity.z = 0.0;
    cmd.acceleration.x = 0.0;
    cmd.acceleration.y = 0.0;
    cmd.acceleration.z = 0.0;
    cmd.yaw = 0.0;
    cmd.yaw_dot = 0.0;

    percep_utils_.reset(new PerceptionUtils(nh));

    for (int i = 0; i < 100; ++i)
    {
      cmd.position.z += 0.01;
      pos_cmd_pub.publish(cmd);
      ros::Duration(0.01).sleep();
    }
    for (int i = 0; i < 100; ++i)
    {
      cmd.position.z -= 0.01;
      pos_cmd_pub.publish(cmd);
      ros::Duration(0.01).sleep();
    }

    R_loop = Eigen::Quaterniond(1, 0, 0, 0).toRotationMatrix();
    T_loop = Eigen::Vector3d(0, 0, 0);
    // 修复：原实现用独立线程跑 cmdCallback，与 visCallback 并发读写 traj_cmd_ 造成堆损坏（gdb 实证）。
    // 改为 ROS 定时器，与其它回调在同一线程串行执行，消除竞态。
    cmd_timer_ = nh.createTimer(ros::Duration(0.01), &FastExplorationFSM::cmdTimerCallback, this);

    /* ---------- 多机协调（use_coord=true 时启用） ---------- */
    nh.param("fsm/use_coord", use_coord_, false);
    nh.param("fsm/drone_id", drone_id_, 1);
    if (use_coord_)
    {
      // 话题由 launch 按机号 remap（/coord/xxx -> /droneN/coord/xxx）
      coord_snap_pub_ = nh.advertise<coord_msgs::FrontierSnapshot>("/coord/frontier_snapshot", 10);
      coord_asgn_sub_ = nh.subscribe(
          "/coord/assignment", 10, &FastExplorationFSM::coordAssignmentCallback, this);
      coord_halt_sub_ =
          nh.subscribe("/coord/halt", 10, &FastExplorationFSM::coordHaltCallback, this);
      coord_snap_timer_ =
          nh.createTimer(ros::Duration(0.2), &FastExplorationFSM::coordSnapshotTimer, this);
      expl_manager_->setCoordEnabled(true);
      ROS_WARN("[COORD] coordination mode ON (drone_id=%d)", drone_id_);
    }
  }

  /* ---------- 多机协调回调 ---------- */

  void FastExplorationFSM::coordAssignmentCallback(const coord_msgs::FrontierAssignmentConstPtr &msg)
  {
    vector<Vector3d> centers;
    centers.reserve(msg->centers.size());
    for (size_t i = 0; i < msg->centers.size(); ++i)
      centers.push_back(Vector3d(msg->centers[i].x, msg->centers[i].y, msg->centers[i].z));
    vector<double> radii(msg->radii.begin(), msg->radii.end());
    expl_manager_->setTaskAssignment(centers, radii, msg->free_explore, msg->partition,
                                     msg->sector_axis, msg->sector_lo, msg->sector_hi);

    // v2.1 故障恢复：协调器检测到有飞机失联后会把幸存机切到全局自由探索。
    // 若某架幸存机已经进入 FINISH（例如本扇区提前扫完），需要允许它重新进入规划，
    // 否则它会一直停在完成态、无法接手失联机的区域。
    if (!halt_received_ && msg->free_explore && !coord_recovery_resumed_ && state_ == FINISH)
    {
      coord_recovery_resumed_ = true;
      {
        std::lock_guard<std::mutex> lock(mtx_plan_);
        plan_.clear();
        receive_traj_ = false;
      }
      fd_->static_state_ = true;
      coord_wait_ = false;
      transitState(PLAN_TRAJ, "coord recovery");
      ROS_WARN("[COORD] recovery: leave FINISH and resume global exploration");
    }

    // 注意（v2.0）：这里不再清除等待标志。旧行为"收到分配即清标志"会使等待状态
    // 每 0.2~0.5s 闪烁一次（分配消息每 tick 都有微小变化），协调器侧的"连续空闲
    // free_wait_time 秒 -> 放开自由探索"兜底计时器因此永远攒不满、从未触发。
    // 现在改为：真正规划出可行目标（SUCCEED）时才退出等待态。
    ROS_INFO_THROTTLE(2.0, "[COORD] assignment v%d updated (%zu regions, free=%d)",
                      msg->version, msg->centers.size(), int(msg->free_explore));
  }

  void FastExplorationFSM::coordHaltCallback(const std_msgs::BoolConstPtr &msg)
  {
    if (!msg->data || halt_received_)
      return;
    halt_received_ = true;
    ROS_WARN("[COORD] ======== HALT received: exploration over (Flight_time=%.1f s, dist=%.1f m) ========",
             flight_time, flight_distance);
  }

  void FastExplorationFSM::coordSnapshotTimer(const ros::TimerEvent &e)
  {
    (void)e;
    if (!fd_->have_odom_)
      return;
    coord_msgs::FrontierSnapshot msg;
    msg.header.stamp = ros::Time::now();
    msg.drone_id = drone_id_;
    msg.pose.position.x = fd_->odom_pos_(0);
    msg.pose.position.y = fd_->odom_pos_(1);
    msg.pose.position.z = fd_->odom_pos_(2);
    msg.pose.orientation.w = fd_->odom_orient_.w();
    msg.pose.orientation.x = fd_->odom_orient_.x();
    msg.pose.orientation.y = fd_->odom_orient_.y();
    msg.pose.orientation.z = fd_->odom_orient_.z();
    msg.yaw = fd_->odom_yaw_;
    if (state_ == FINISH)
      msg.state = 1;  // 已完成
    else if (use_coord_ && coord_wait_)
      msg.state = 2;  // 无前沿等待分配
    else if (state_ == INIT || state_ == WAIT_TRIGGER || state_ == YAWING)
      msg.state = 3;  // 准备中（起飞/偏航/等待触发）：此阶段原地运动，不应被判定为卡住
    else
      msg.state = 0;  // 探索中

    vector<Vector3d> centers;
    vector<double> sizes;
    expl_manager_->getFrontiersBrief(centers, sizes);
    msg.centers.resize(centers.size());
    msg.sizes.resize(centers.size());
    for (size_t i = 0; i < centers.size(); ++i)
    {
      msg.centers[i].x = centers[i](0);
      msg.centers[i].y = centers[i](1);
      msg.centers[i].z = centers[i](2);
      msg.sizes[i] = float(sizes[i]);
    }
    coord_snap_pub_.publish(msg);
  }

  void FastExplorationFSM::new_thread()
  {
    while (!flightEnd)
    {
      cmdCallback();
      usleep(10000);
    }
  }

  void FastExplorationFSM::pgTVioCallback(geometry_msgs::Pose msg)
  {
    // World to odom
    Eigen::Quaterniond q =
        Eigen::Quaterniond(msg.orientation.w, msg.orientation.x, msg.orientation.y, msg.orientation.z);
    R_loop = q.toRotationMatrix();
    T_loop << msg.position.x, msg.position.y, msg.position.z;

    // cout << "R_loop: " << R_loop << endl;
    // cout << "T_loop: " << T_loop << endl;
  }

  bool FastExplorationFSM::newPathCallback(vector<state> path, int start_index)
  {
    // cout<<"add points to plan_"<<endl;
    mtx_plan_.lock();
    int plan_size = plan_.size();

    if ((plan_size - 1 - start_index) < 0)
    {
      std::cout << "Already published the point A" << std::endl;
      std::cout << "plan_size: " << plan_size << std::endl;
      mtx_plan_.unlock();
      return false;
    }
    else
    {
      plan_.erase(plan_.end() - start_index, plan_.end());

      for (int i = 0; i < path.size(); i++)
      {
        plan_.push_back(path[i]);
      }
      traj_id_++;
    }
    receive_traj_ = true;
    cout << bold << green << "plan_ has points: " << plan_.size() << reset << endl;
    mtx_plan_.unlock();
    return true;
  }

  void FastExplorationFSM::drawFOV(const vector<Eigen::Vector3d> &list1, const vector<Eigen::Vector3d> &list2)
  {
    // cout<<"draw FOV"<<endl;
    visualization_msgs::Marker mk;
    mk.header.frame_id = "world";
    mk.header.stamp = ros::Time::now();
    mk.id = 0;
    mk.ns = "current_pose";
    mk.type = visualization_msgs::Marker::LINE_LIST;
    mk.pose.orientation.x = 0.0;
    mk.pose.orientation.y = 0.0;
    mk.pose.orientation.z = 0.0;
    mk.pose.orientation.w = 1.0;
    mk.color.r = 1.0;
    mk.color.g = 0.0;
    mk.color.b = 0.0;
    mk.color.a = 1.0;
    mk.scale.x = 0.04;
    mk.scale.y = 0.04;
    mk.scale.z = 0.04;

    // Clean old marker
    mk.action = visualization_msgs::Marker::DELETE;
    cmd_vis_pub.publish(mk);

    if (list1.size() == 0)
      return;

    // Pub new marker
    geometry_msgs::Point pt;
    for (int i = 0; i < int(list1.size()); ++i)
    {
      pt.x = list1[i](0);
      pt.y = list1[i](1);
      pt.z = list1[i](2);
      mk.points.push_back(pt);

      pt.x = list2[i](0);
      pt.y = list2[i](1);
      pt.z = list2[i](2);
      mk.points.push_back(pt);
    }
    mk.action = visualization_msgs::Marker::ADD;
    cmd_vis_pub.publish(mk);
  }

  void FastExplorationFSM::drawCmd(const Eigen::Vector3d &pos, const Eigen::Vector3d &vec, const int &id, const Eigen::Vector4d &color)
  {
    // cout<<"draw Cmd"<<endl;
    visualization_msgs::Marker mk_state;
    mk_state.header.frame_id = "world";
    mk_state.header.stamp = ros::Time::now();
    mk_state.id = id;
    mk_state.type = visualization_msgs::Marker::ARROW;
    mk_state.action = visualization_msgs::Marker::ADD;

    mk_state.pose.orientation.w = 1.0;
    mk_state.scale.x = 0.1;
    mk_state.scale.y = 0.2;
    mk_state.scale.z = 0.3;

    geometry_msgs::Point pt;
    pt.x = pos(0);
    pt.y = pos(1);
    pt.z = pos(2);
    mk_state.points.push_back(pt);

    pt.x = pos(0) + vec(0);
    pt.y = pos(1) + vec(1);
    pt.z = pos(2) + vec(2);
    mk_state.points.push_back(pt);

    mk_state.color.r = color(0);
    mk_state.color.g = color(1);
    mk_state.color.b = color(2);
    mk_state.color.a = color(3);

    cmd_vis_pub.publish(mk_state);
  }

  void FastExplorationFSM::displayTrajWithColor(vector<Eigen::Vector3d> path, double resolution, Eigen::Vector4d color, int id)
  {
    visualization_msgs::Marker mk;
    mk.header.frame_id = "world";
    mk.header.stamp = ros::Time::now();
    mk.type = visualization_msgs::Marker::SPHERE_LIST;
    mk.action = visualization_msgs::Marker::DELETE;
    mk.id = id;

    traj_pub.publish(mk);

    mk.action = visualization_msgs::Marker::ADD;
    mk.pose.orientation.x = 0.0;
    mk.pose.orientation.y = 0.0;
    mk.pose.orientation.z = 0.0;
    mk.pose.orientation.w = 1.0;

    mk.color.r = color(0);
    mk.color.g = color(1);
    mk.color.b = color(2);
    mk.color.a = color(3);

    mk.scale.x = resolution;
    mk.scale.y = resolution;
    mk.scale.z = resolution;

    //输出飞行轨迹
    // fstream fp;
    // fp.open("/home/zyh/data.txt",ios::out|ios::app);
    geometry_msgs::Point pt;
    for (int i = 0; i < int(path.size()); i++)
    {
      // fp<<path[i](0)<<","<<path[i](1)<<","<<path[i](2)<<endl;
      pt.x = path[i](0);
      pt.y = path[i](1);
      pt.z = path[i](2);
      mk.points.push_back(pt);
    }
    traj_pub.publish(mk);
    ros::Duration(0.001).sleep();
  }

  void FastExplorationFSM::visCallback(const ros::TimerEvent &e)
  {
    // 多机场景按机号着色执行轨迹（1=橙红 2=绿 3=蓝），便于 RViz 区分各机
    Eigen::Vector4d traj_color(0, 0, 1, 1);
    if (drone_id_ == 1)
      traj_color = Eigen::Vector4d(1.0, 0.3, 0.0, 1);
    else if (drone_id_ == 2)
      traj_color = Eigen::Vector4d(0.0, 0.85, 0.1, 1);
    else if (drone_id_ == 3)
      traj_color = Eigen::Vector4d(0.1, 0.4, 1.0, 1);
    displayTrajWithColor(traj_cmd_, 0.05, traj_color, 5);
  }

  void FastExplorationFSM::cmdTimerCallback(const ros::TimerEvent &e)
  {
    cmdCallback();

    // OOM 修复：每 10 秒回收一次 glibc 空闲堆（malloc_trim），把高频规划产生的
    // 分配器高水位归还操作系统，防止极端情况下 RSS 涨到数 GB 被 OOM 杀死。
    ros::Time now = ros::Time::now();
    if ((now - last_trim_time_).toSec() > 10.0)
    {
      last_trim_time_ = now;
      malloc_trim(0);
    }
  }

  void FastExplorationFSM::cmdCallback()
  {
    if (!receive_traj_)
      return;

    // cout<<"send cmd order"<<endl;
    mtx_plan_.lock();
    ros::Time time_now = ros::Time::now();

    Eigen::Vector3d pos, vel, acc, pos_f;
    double yaw, yawdot;

    state next_goal;
    next_goal = plan_.front();
    
    // cout<<bold<<red<<plan_.size()<<reset<<endl;
    if (plan_.size() > 1)
    {
      plan_.pop_front();
    }
    else
    {
      cout << bold << red << "plan_ has zero point!" << reset << endl;
      plan_.pop_front();
      state stop_flight;
      stop_flight.setPos(next_goal.pos[0], next_goal.pos[1], next_goal.pos[2]);
      stop_flight.setVel(0, 0, 0);
      stop_flight.setAccel(0, 0, 0);
      stop_flight.yaw = next_goal.yaw;
      stop_flight.dyaw = next_goal.dyaw;
      stop_flight.ddyaw = next_goal.ddyaw;
      plan_.push_back(stop_flight);
      // flightEnd = true;
      if (state_ == YAWING)
      {
        cout << bold << green << next_goal.yaw << reset << endl;
        transitState(PLAN_TRAJ, "FSM");
      }
    }
    mtx_plan_.unlock();

    pos = next_goal.pos;
    vel = next_goal.vel;
    acc = next_goal.accel;
    yaw = next_goal.yaw;
    if (isLoopCorrection)
    {
      pos = R_loop.transpose() * (pos - T_loop);
      vel = R_loop.transpose() * vel;
      acc = R_loop.transpose() * acc;

      Eigen::Vector3d yaw_dir(cos(yaw), sin(yaw), 0);
      yaw_dir = R_loop.transpose() * yaw_dir;
      yaw = atan2(yaw_dir[1], yaw_dir[0]);
    }
    yawdot = next_goal.dyaw;
    cmd.header.stamp = time_now;
    cmd.header.frame_id = "world";
    cmd.trajectory_flag = quadrotor_msgs::PositionCommand::TRAJECTORY_STATUS_READY;
    cmd.trajectory_id = traj_id_;

    cmd.position.x = pos(0);
    cmd.position.y = pos(1);
    cmd.position.z = pos(2);

    cmd.velocity.x = vel(0);
    cmd.velocity.y = vel(1);
    cmd.velocity.z = vel(2);

    cmd.acceleration.x = acc(0);
    cmd.acceleration.y = acc(1);
    cmd.acceleration.z = acc(2);

    // if(fabs(yaw - last_yaw_) > 1)
    // {
    //   if(yaw > 0)
    //     yaw = 2*M_PI - yaw;
    //   else yaw = 2*M_PI + yaw;
    // }

    cmd.yaw = yaw;
    cmd.yaw_dot = yawdot;

    if(traj_cmd_.size() > 0 && (pos - traj_cmd_.back()).norm() > 0.5)
      cout<< bold << red << "traj error: " << (pos - traj_cmd_.back()).norm() << reset << endl;

    last_yaw_ = cmd.yaw;

    pos_cmd_pub.publish(cmd);

    percep_utils_->setPose(pos, yaw);
    vector<Eigen::Vector3d> l1, l2;
    percep_utils_->getFOV(l1, l2);
    // cout<<"getFOV: "<<l1.size()<<","<<l2.size()<<endl;
    drawFOV(l1, l2);

    // cout << green << plan_.size() << reset << endl;

    if (state_ != FINISH)
    {
      flight_CtrCost += 0.01 * (next_goal.jerk).squaredNorm();
      flight_distance += (new_state.pos - next_goal.pos).norm();
    }

    new_state = next_goal;

    Eigen::Vector3d dir(cos(yaw), sin(yaw), 0.0);
    drawCmd(pos, 2 * dir, 2, Eigen::Vector4d(1, 1, 0, 0.7));

    traj_cmd_.push_back(pos);
    if (traj_cmd_.size() > 10000)
      traj_cmd_.erase(traj_cmd_.begin(), traj_cmd_.begin() + 2000);

    // mtx_plan_.unlock();
  }

  void FastExplorationFSM::FSMCallback(const ros::TimerEvent &e)
  {
    ROS_INFO_STREAM_THROTTLE(1.0, "[FSM]: state: " << fd_->state_str_[int(state_)]);

    switch (state_)
    {
    case INIT:
    {
      // Wait for odometry ready
      if (!fd_->have_odom_)
      {
        ROS_WARN_THROTTLE(1.0, "no odom.");
        return;
      }
      // Go to wait trigger when odom is ok
      transitState(WAIT_TRIGGER, "FSM");
      break;
    }

    case WAIT_TRIGGER:
    {
      // Do nothing but wait for trigger
      ROS_WARN_THROTTLE(1.0, "wait for trigger.");
      break;
    }

    case YAWING:
    {
      ROS_WARN_THROTTLE(1.0, "YAWING.");
      if (yawing == false)
      {
        Eigen::Vector3d init_yaw(fd_->odom_yaw_, 0, 0);
        expl_manager_->yawingBeforeFlight(init_yaw);

        mtx_plan_.lock();
        state init_state;
        Eigen::Vector3d init_pt(fp_->init_x, fp_->init_y, fp_->init_z);
        init_state.setPos(init_pt);
        init_state.setVel(fd_->start_vel_);
        init_state.setAccel(fd_->start_acc_);
        init_state.yaw = fd_->start_yaw_(0);
        init_state.dyaw = fd_->start_yaw_(1);
        init_state.ddyaw = fd_->start_yaw_(2);
        plan_.push_back(init_state);
        mtx_plan_.unlock();

        vector<state> newPlanList;

        auto info = &planner_manager_->local_data_;
        double yaw_time = info->yaw_traj_.getTimeSum();
        cout << bold << green << yaw_time << reset << endl;
        cout << bold << green << info->yaw_traj_.evaluateDeBoorT(yaw_time)[0] << reset << endl;
        cout << bold << green << info->yawdot_traj_.evaluateDeBoorT(yaw_time)[0] << reset << endl;
        cout << bold << green << info->yawdotdot_traj_.evaluateDeBoorT(yaw_time)[0] << reset << endl;
        for (double i = 0.01; i <= yaw_time + 1e-1; i = i + 0.01)
        {
          state temp_state;
          temp_state.pos = init_pt;
          Eigen::Vector3d temp_vel(0, 0, 0);
          temp_state.vel = temp_vel;
          temp_state.accel = temp_vel;
          temp_state.jerk = temp_vel;
          temp_state.yaw = info->yaw_traj_.evaluateDeBoorT(i)[0];
          temp_state.dyaw = info->yawdot_traj_.evaluateDeBoorT(i)[0];
          temp_state.ddyaw = info->yawdotdot_traj_.evaluateDeBoorT(i)[0];
          newPlanList.push_back(temp_state);
        }

        bool addPath = newPathCallback(newPlanList, 0);
        // receive_traj_ = true;
      }
      yawing = true;
      break;
    }

    case FINISH:
    {
      ROS_INFO_THROTTLE(1.0, "finish exploration.");
      // 带上机号标识：多机日志混合时用于区分各机指标
      cout << bold << green << "[Flight_time]: " << flight_time << " (drone " << drone_id_ << ")" << reset
           << endl;
      cout << bold << green << "[Flight_cost]: " << flight_CtrCost << " (drone " << drone_id_ << ")"
           << reset << endl;
      cout << bold << green << "[Flight_dist]: " << flight_distance << " (drone " << drone_id_ << ")"
           << reset << endl;
      if (!isfinished)
      {
        // 原代码写死作者服务器路径，这里改为可配置（留空则不写文件）
        if (!fp_->result_file_.empty())
        {
          ofstream file(fp_->result_file_, ios::app);
          file << "[Flight_time]: " << flight_time << "\n"
               << "[Flight_cost]: " << flight_CtrCost << "\n"
               << "[Flight_dist]: " << flight_distance << std::endl;
        }
             
        isfinished = true;
      }

      break;
    }

    case PLAN_TRAJ:
    {
      // 多机协调：处于"等待分配"时把规划尝试降频到 0.5s 一次，避免空转
      if (use_coord_ && coord_wait_ && (ros::Time::now() - coord_wait_start_).toSec() < 0.5)
        break;

      // OOM 修复：规划最小间隔 0.2s。正常重规划节奏为 2-3Hz（间隔 0.3-0.5s）不受影响；
      // "抖动"状态下的 10-20Hz 高频重规划循环被限制——每次规划触发全量前沿搜索与
      // 大量临时分配（经 heaptrack 确认是分配热点），是内存高水位暴涨的主要来源。
      if ((ros::Time::now() - last_plan_time_).toSec() < 0.2)
        break;
      last_plan_time_ = ros::Time::now();

      double startPlan = ros::Time::now().toSec();
      if (fd_->static_state_)
      {
        // Plan from static state (hover)
        fd_->start_pt_ = fd_->odom_pos_;
        fd_->start_vel_ = fd_->odom_vel_;
        fd_->start_acc_.setZero();

        fd_->start_yaw_(0) = fd_->odom_yaw_;
        fd_->start_yaw_(1) = fd_->start_yaw_(2) = 0.0;
        // mtx_plan_.lock();
        state init_state;
        init_state.setPos(fd_->start_pt_);
        init_state.setVel(fd_->start_vel_);
        init_state.setAccel(fd_->start_acc_);
        init_state.yaw = fd_->start_yaw_(0);
        init_state.dyaw = fd_->start_yaw_(1);
        init_state.ddyaw = fd_->start_yaw_(2);
        if (plan_.size() == 0)
          plan_.push_back(init_state);
      }
      else
      {
        state curState = new_state;
        plan_state = curState;
      }

      // Inform traj_server the replanning
      // replan_pub_.publish(std_msgs::Empty());
      int res = callExplorationPlanner();
      double temp_t = ros::Time::now().toSec() - startPlan;
      adaptive_t = max(int(ceil(temp_t * 100 * 1.3)), 10);
      if (res == SUCCEED)
      {
        if (coord_wait_)
        {
          coord_wait_ = false;
          ROS_INFO("[COORD] target acquired, resume flying");
        }
        plan_cost_time += ros::Time::now().toSec() - startPlan;
        plan_loop_num++;
        transitState(PUB_TRAJ, "FSM");

        // fd_->static_state_ = false;
        // // transitState(EXEC_TRAJ, "FSM");

        // thread vis_thread(&FastExplorationFSM::visualize, this);
        // vis_thread.detach();
      }
      else if (res == NO_FRONTIER)
      {
        // 多机协调：区分"暂时没分到任务"与"真正探索完成"
        if (use_coord_ && !halt_received_)
        {
          if (expl_manager_->coordFilterEmpty())
          {
            // 只是本地没有被分配到的区域可探索 -> 等待协调器重新分配，不结束
            fd_->static_state_ = true;
            if (!coord_wait_)
            {
              coord_wait_ = true;
              coord_wait_start_ = ros::Time::now();
              ROS_WARN("[COORD] no assigned task to execute, waiting for coordinator...");
            }
            break;
          }
          // 全局确实没有前沿（本机视角）：进入完成态，等待协调器 halt 统一收尾
          plan_cost_time += ros::Time::now().toSec() - startPlan;
          plan_loop_num++;
          cout << "finish" << endl;
          transitState(FINISH, "FSM");
          fd_->static_state_ = true;
          clearVisMarker();
          flight_time = ros::Time::now().toSec() - flight_start;
          ROS_WARN("[COORD] local exploration finished, waiting for halt signal");
          break;
        }

        plan_cost_time += ros::Time::now().toSec() - startPlan;
        plan_loop_num++;
        cout << "finish" << endl;
        transitState(FINISH, "FSM");
        fd_->static_state_ = true;
        clearVisMarker();
        //输出飞行关键参数
        flight_time = ros::Time::now().toSec() - flight_start;
        // flight_finished = ros::Time::now().toSec() - flight_start;
      }
      else if (res == FAIL)
      {
        // Still in PLAN_TRAJ state, keep replanning
        ROS_WARN("plan fail");
        // 卡死自愈：持续失败上报，超时后把不可达目标加入黑名单（单机/多机均生效）
        expl_manager_->notifyPlanFail();
        // fd_->static_state_ = true;
      }
      break;
    }

    case PUB_TRAJ:
    {
      // fd_->static_state_ = false;
      // transitState(EXEC_TRAJ, "FSM");

      // thread vis_thread(&FastExplorationFSM::visualize, this);
      // vis_thread.detach();
      // break;
      // double dt = (ros::Time::now() - fd_->newest_traj_.start_time).toSec();
      if ((ros::Time::now() - plan_success_time).toSec() > 0)
      {
        // bspline_pub_.publish(fd_->newest_traj_);
        fd_->static_state_ = false;
        transitState(EXEC_TRAJ, "FSM");        
      }
      break;
    }

    case EXEC_TRAJ:
    {
      // LocalTrajData *info = &planner_manager_->local_data_;
      double t_cur = (ros::Time::now() - plan_success_time).toSec();

      // Replan if traj is almost fully executed
      // double time_to_end = info->first_duration - t_cur;
      // if (state_ != YAWING && plan_.size() < 2)
      // {

      //   flightEnd = true;
      //   transitState(FINISH, "FSM");

      //   return;
      // }

      if (plan_.size() < 100)
      {
        if (state_ != FINISH)
        {
          transitState(PLAN_TRAJ, "FSM");
          ROS_WARN("Replan: plan size less than 100=================================");
          return;
        }
      }

      // Replan if next frontier to be visited is covered
      if (t_cur > fp_->replan_thresh2_ && expl_manager_->frontier_finder_->isFrontierCovered())
      {
        transitState(PLAN_TRAJ, "FSM");
        ROS_WARN("Replan: cluster covered=====================================");
        return;
      }

      if (t_cur > 1)
      {
        transitState(PLAN_TRAJ, "FSM");
        ROS_WARN("Replan: traj exec half======================================");
        return;
      }
      // Replan after some time
      if (t_cur > fp_->replan_thresh3_ && !classic_)
      {
        transitState(PLAN_TRAJ, "FSM");
        ROS_WARN("Replan: periodic call=======================================");
      }
      break;
    }
    }
  }

  int FastExplorationFSM::callExplorationPlanner()
  {
    ros::Time time_r = ros::Time::now() + ros::Duration(fp_->replan_time_);

    Eigen::Vector3d plan_start_pos, plan_start_vel, plan_start_acc, plan_start_yaw;

    state A;
    int k_end_whole;

    // If k_end_whole=0, then A = plan_.back() = plan_[plan_.size() - 1]
    k_end_whole = std::max((int)plan_.size() - adaptive_t, 0);
    cout << bold << green << "plan_size: " << plan_.size() << reset << endl;
    A = plan_[plan_.size() - 1 - k_end_whole];
    plan_start_pos = A.pos;
    plan_start_vel = A.vel;
    plan_start_acc = A.accel;
    plan_start_yaw[0] = A.yaw;
    plan_start_yaw[1] = A.dyaw;
    plan_start_yaw[2] = A.ddyaw;

    int res = expl_manager_->planExploreMotion(plan_start_pos, plan_start_vel, plan_start_acc,
                                               plan_start_yaw);
    classic_ = false;

    double cur_replan_start = ros::Time::now().toSec();

    if (res == SUCCEED)
    {
      cout << bold << green << "exploration planning success" << reset << endl;
      auto info = &planner_manager_->local_data_;
      info->start_time_ = (ros::Time::now() - time_r).toSec() > 0 ? ros::Time::now() : time_r;

      vector<state> newPlanList;

      double traj_duration = info->duration_;

      for (double i = 0.01; i <= traj_duration - 1e-2; i = i + 0.01)
      {
        state temp_state;
        temp_state.pos = info->position_traj_.evaluateDeBoorT(i);
        temp_state.vel = info->velocity_traj_.evaluateDeBoorT(i);
        temp_state.accel = info->acceleration_traj_.evaluateDeBoorT(i);
        temp_state.jerk = info->jerk_traj_.evaluateDeBoorT(i);

        if (i == 0.01 && (plan_start_pos - temp_state.pos).norm() > 0.5)
        {
          cout << bold << red << "traj plan error: " << (temp_state.pos - plan_start_pos).norm() << reset << endl;
          return FAIL;
        }

        //如果小范围多边界区域  则传感器大范围旋转
        if (expl_manager_->manyViewPoints && i >= expl_manager_->first_time_duration)
        {
          double temp_t = i - expl_manager_->first_time_duration;
          temp_state.yaw = info->yaw1_traj_.evaluateDeBoorT(temp_t)[0];
          temp_state.dyaw = info->yawdot1_traj_.evaluateDeBoorT(temp_t)[0];
          temp_state.ddyaw = info->yawdotdot1_traj_.evaluateDeBoorT(temp_t)[0];
          if(temp_state.dyaw > 5)
            return FAIL;
        }
        else
        {
          temp_state.yaw = info->yaw_traj_.evaluateDeBoorT(i)[0];
          temp_state.dyaw = info->yawdot_traj_.evaluateDeBoorT(i)[0];
          temp_state.ddyaw = info->yawdotdot_traj_.evaluateDeBoorT(i)[0];
          if(temp_state.dyaw > 5)
            return FAIL;
        }

        newPlanList.push_back(temp_state);
      }

      bool addPath = newPathCallback(newPlanList, k_end_whole);
      if (!addPath)
      {
        cout << "already publish A. Replan again." << endl;
        //修改规划为重规划
        return FAIL;
      }

      plan_success_time = ros::Time::now();

      // bspline::Bspline bspline;
      // bspline.order = planner_manager_->pp_.bspline_degree_;
      // bspline.start_time = info->start_time_;
      // bspline.traj_id = info->traj_id_;
      // Eigen::MatrixXd pos_pts = info->position_traj_.getControlPoint();
      // for (int i = 0; i < pos_pts.rows(); ++i)
      // {
      //   geometry_msgs::Point pt;
      //   pt.x = pos_pts(i, 0);
      //   pt.y = pos_pts(i, 1);
      //   pt.z = pos_pts(i, 2);
      //   bspline.pos_pts.push_back(pt);
      // }
      // Eigen::VectorXd knots = info->position_traj_.getKnot();
      // for (int i = 0; i < knots.rows(); ++i)
      // {
      //   bspline.knots.push_back(knots(i));
      // }
      // Eigen::MatrixXd yaw_pts = info->yaw_traj_.getControlPoint();
      // for (int i = 0; i < yaw_pts.rows(); ++i)
      // {
      //   double yaw = yaw_pts(i, 0);
      //   bspline.yaw_pts.push_back(yaw);
      // }
      // bspline.yaw_dt = info->yaw_traj_.getKnotSpan();
      // fd_->newest_traj_ = bspline;
    }
    return res;
  }

  void FastExplorationFSM::visualize(const ros::TimerEvent &e)
  {
    auto info = &planner_manager_->local_data_;
    auto plan_data = &planner_manager_->plan_data_;
    auto ed_ptr = expl_manager_->ed_;

    // Draw updated box
    // Vector3d bmin, bmax;
    // planner_manager_->edt_environment_->sdf_map_->getUpdatedBox(bmin, bmax);
    // visualization_->drawBox((bmin + bmax) / 2.0, bmax - bmin, Vector4d(0, 1, 0, 0.3), "updated_box", 0,
    // 4);

    // Draw frontier
    for (int i = 0; i < ed_ptr->frontiers_.size(); ++i)
    {
      visualization_->drawCubes(ed_ptr->frontiers_[i], 0.1,
                                visualization_->getColor(double(i) / ed_ptr->frontiers_.size(), 0.4),
                                "frontier", i, 4);
      // visualization_->drawBox(ed_ptr->frontier_boxes_[i].first, ed_ptr->frontier_boxes_[i].second,
      //                         Vector4d(0.5, 0, 1, 0.3), "frontier_boxes", i, 4);
    }
    for (int i = ed_ptr->frontiers_.size(); i < 15; ++i)
    {
      visualization_->drawCubes({}, 0.1, Vector4d(0, 0, 0, 1), "frontier", i, 4);
      // visualization_->drawBox(Vector3d(0, 0, 0), Vector3d(0, 0, 0), Vector4d(1, 0, 0, 0.3),
      // "frontier_boxes", i, 4);
    }
    visualization_->drawLines(ed_ptr->refined_tour_, 0.07, Vector4d(0, 0, 1, 1), "refined_tour", 0, 6);

    visualization_->drawBspline(info->position_traj_, 0.1, Vector4d(1.0, 0.0, 0.0, 1), false, 0.15,
                                Vector4d(1, 1, 0, 1));
    visualization_->drawLines(plan_data->kino_path_, 0.1, Vector4d(0, 0.5, 0, 1), "kino_path", 1, 6);
    // visualization_->drawSpheres(plan_data->kino_path_, 0.1, Vector4d(1, 1, 1, 1), "kino_path", 0, 0);
    visualization_->drawLines(ed_ptr->path_next_goal_, 0.05, Vector4d(1, 1, 0, 1), "next_goal", 2, 6);
  }

  void FastExplorationFSM::clearVisMarker()
  {
    // visualization_->drawSpheres({}, 0.2, Vector4d(0, 0.5, 0, 1), "points", 0, 6);
    // visualization_->drawLines({}, 0.07, Vector4d(0, 0.5, 0, 1), "global_tour", 0, 6);
    // visualization_->drawSpheres({}, 0.2, Vector4d(0, 0, 1, 1), "refined_pts", 0, 6);
    // visualization_->drawLines({}, {}, 0.05, Vector4d(0.5, 0, 1, 1), "refined_view", 0, 6);
    // visualization_->drawLines({}, 0.07, Vector4d(0, 0, 1, 1), "refined_tour", 0, 6);
    // visualization_->drawSpheres({}, 0.1, Vector4d(0, 0, 1, 1), "B-Spline", 0, 0);

    // visualization_->drawLines({}, {}, 0.03, Vector4d(1, 0, 0, 1), "current_pose", 0, 6);
  }

  void FastExplorationFSM::frontierCallback(const ros::TimerEvent &e)
  {
    static int delay = 0;
    if (++delay < 5)
      return;

    if (state_ == WAIT_TRIGGER || state_ == YAWING || state_ == FINISH)
    {
      auto ft = expl_manager_->frontier_finder_;
      auto ed = expl_manager_->ed_;
      ft->searchFrontiers();
      ft->computeFrontiersToVisit();
      ft->updateFrontierCostMatrix();

      ft->getFrontiers(ed->frontiers_);
      ft->getFrontierBoxes(ed->frontier_boxes_);

      // Draw frontier and bounding box
      for (int i = 0; i < ed->frontiers_.size(); ++i)
      {
        visualization_->drawCubes(ed->frontiers_[i], 0.1,
                                  visualization_->getColor(double(i) / ed->frontiers_.size(), 0.4),
                                  "frontier", i, 4);
        // visualization_->drawBox(ed->frontier_boxes_[i].first, ed->frontier_boxes_[i].second,
        // Vector4d(0.5, 0, 1, 0.3),
        //                         "frontier_boxes", i, 4);
      }
      for (int i = ed->frontiers_.size(); i < 50; ++i)
      {
        visualization_->drawCubes({}, 0.1, Vector4d(0, 0, 0, 1), "frontier", i, 4);
        // visualization_->drawBox(Vector3d(0, 0, 0), Vector3d(0, 0, 0), Vector4d(1, 0, 0, 0.3),
        // "frontier_boxes", i, 4);
      }
    }

  }

  void FastExplorationFSM::triggerCallback(const nav_msgs::PathConstPtr &msg)
  {
    if (msg->poses[0].pose.position.z < -0.1)
      return;
    if (state_ != WAIT_TRIGGER)
      return;
    fd_->trigger_ = true;
    cout << "Triggered!" << endl;
    transitState(YAWING, "triggerCallback");
    flight_start = ros::Time::now().toSec();
  }

  void FastExplorationFSM::safetyCallback(const ros::TimerEvent &e)
  {
    if (state_ == EXPL_STATE::EXEC_TRAJ)
    {
      // mtx_plan_.lock();
      for (int i = 0; i < plan_.size(); i++)
      {
        Eigen::Vector3d cur_plan_point = plan_[i].pos;

        auto edt_env = planner_manager_->sdf_map_;
        if (edt_env->getInflateOccupancy(cur_plan_point) == 1)
        {
          ROS_WARN("current traj in collision.");
          // adaptive_t = 2;
          transitState(PLAN_TRAJ, "safetyCallback");
          break;
        }
      }
      // mtx_plan_.unlock();
      // Check safety and trigger replan if necessary
      // double dist;
      // bool safe = planner_manager_->checkTrajCollision(dist);
      // if (!safe)
      // {
      //   ROS_WARN("Replan: collision detected==================================");
      //   transitState(PLAN_TRAJ, "safetyCallback");
      // }
    }
  }

  void FastExplorationFSM::odometryCallback(const nav_msgs::OdometryConstPtr &msg)
  {
    fd_->odom_pos_(0) = msg->pose.pose.position.x;
    fd_->odom_pos_(1) = msg->pose.pose.position.y;
    fd_->odom_pos_(2) = msg->pose.pose.position.z;

    fd_->odom_vel_(0) = msg->twist.twist.linear.x;
    fd_->odom_vel_(1) = msg->twist.twist.linear.y;
    fd_->odom_vel_(2) = msg->twist.twist.linear.z;

    fd_->odom_orient_.w() = msg->pose.pose.orientation.w;
    fd_->odom_orient_.x() = msg->pose.pose.orientation.x;
    fd_->odom_orient_.y() = msg->pose.pose.orientation.y;
    fd_->odom_orient_.z() = msg->pose.pose.orientation.z;

    Eigen::Vector3d rot_x = fd_->odom_orient_.toRotationMatrix().block<3, 1>(0, 0);
    fd_->odom_yaw_ = atan2(rot_x(1), rot_x(0));

    // 原代码写死作者服务器路径，这里改为可配置（留空则不记录），多机时每机写独立文件
    if (!fp_->path_file_.empty())
    {
      ofstream file(fp_->path_file_, ios::app);
      file << msg->pose.pose.position.x << "," << msg->pose.pose.position.y << "," << msg->pose.pose.position.z << std::endl;
    }

    fd_->have_odom_ = true;
  }

  void FastExplorationFSM::transitState(EXPL_STATE new_state, string pos_call)
  {
    int pre_s = int(state_);
    state_ = new_state;
    cout << "[" + pos_call + "]: from " + fd_->state_str_[pre_s] + " to " + fd_->state_str_[int(new_state)]
         << endl;
  }
} // namespace fast_planner
