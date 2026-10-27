#ifndef _EXPLORATION_MANAGER_H_
#define _EXPLORATION_MANAGER_H_

#include <ros/ros.h>
#include <Eigen/Eigen>
#include <memory>
#include <vector>

using Eigen::Vector3d;
using std::shared_ptr;
using std::unique_ptr;
using std::vector;

namespace fast_planner {
class EDTEnvironment;
class SDFMap;
class FastPlannerManager;
class FrontierFinder;
struct ExplorationParam;
struct ExplorationData;

enum EXPL_RESULT { NO_FRONTIER, FAIL, SUCCEED };

class FastExplorationManager {
public:
  FastExplorationManager();
  ~FastExplorationManager();

  void initialize(ros::NodeHandle& nh);

  int planExploreMotion(const Vector3d& pos, const Vector3d& vel, const Vector3d& acc,
                        const Vector3d& yaw);

  // Benchmark method, classic frontier and rapid frontier
  int classicFrontier(const Vector3d& pos, const double& yaw);
  int rapidFrontier(const Vector3d& pos, const Vector3d& vel, const double& yaw, bool& classic);

  void yawingBeforeFlight(const Vector3d& yaw);

  /* ---------- 多机协调接口（use_coord=true 时由 FSM 驱动，默认关闭不影响单机行为） ---------- */
  // 开启/关闭任务过滤
  void setCoordEnabled(bool enable) { coord_enabled_ = enable; }
  bool coordEnabled() const { return coord_enabled_; }
  // 更新协调器下发的任务区域（中心 + 半径）、自由探索标志与 v2.0 扇区信息
  void setTaskAssignment(const vector<Vector3d>& centers, const vector<double>& radii, bool free_explore,
                         bool partition = false, int sector_axis = 0, double sector_lo = -1e6,
                         double sector_hi = 1e6);
  // 本机前沿摘要（转发给 fsm 发布快照）
  void getFrontiersBrief(vector<Vector3d>& centers, vector<double>& sizes);
  // 上一次 NO_FRONTIER 是否是"任务过滤清空"导致（true=只是本地没分到活，等待即可；
  // false=全局确实没有前沿，进入完成态）
  bool coordFilterEmpty() const { return coord_filter_emptied_; }
  // 卡死自愈：规划失败上报（连续失败超时 -> 将最近目标加入黑名单，跳过不可达目标）
  void notifyPlanFail();

  shared_ptr<ExplorationData> ed_;
  shared_ptr<ExplorationParam> ep_;
  shared_ptr<FastPlannerManager> planner_manager_;
  shared_ptr<FrontierFinder> frontier_finder_;

  //是否小范围多边界  边界聚集区域
  bool manyViewPoints = true;
  double first_time_duration = 0;
  bool kino_use_shorten = false;
  // unique_ptr<ViewFinder> view_finder_;

private:
  shared_ptr<EDTEnvironment> edt_environment_;
  shared_ptr<SDFMap> sdf_map_;

  // 多机协调状态
  bool coord_enabled_ = false;
  bool coord_free_explore_ = true;
  bool coord_filter_emptied_ = false;
  bool coord_partition_ = false;      // v2.0：协调器启用按扇区划分
  int sector_axis_ = 0;               // 0=x, 1=y
  double sector_lo_ = -1e6, sector_hi_ = 1e6;
  vector<Vector3d> task_centers_;
  vector<double> task_radii_;

  // 点是否落在任一分配任务区域内（含 0.5m 放宽容差）
  bool inTaskRegion(const Vector3d& pt);

  // v2.0：点是否落在本机扇区内（沿 sector_axis，含 0.6m 放宽容差）
  bool inSector(const Vector3d& pt);

  // 卡死自愈状态：失败目标黑名单与连续失败计时
  vector<Vector3d> blocked_centers_;
  Vector3d last_plan_target_ = Vector3d::Zero();
  ros::Time fail_streak_start_;
  ros::Time last_fail_time_;
  double min_target_dist_ = 0.0;  // 抖动防护：跳过与当前位置距离小于该值的目标（0=关闭）

  // Find optimal tour for coarse viewpoints of all frontiers
  void findGlobalTour(const Vector3d& cur_pos, const Vector3d& cur_vel, const Vector3d cur_yaw,
                      vector<int>& indices);

  // Refine local tour for next few frontiers, using more diverse viewpoints
  void refineLocalTour(const Vector3d& cur_pos, const Vector3d& cur_vel, const Vector3d& cur_yaw,
                       const vector<vector<Vector3d>>& n_points, const vector<vector<double>>& n_yaws,
                       vector<Vector3d>& refined_pts, vector<double>& refined_yaws, vector<bool>& smallAreaData, vector<bool>& smallArea);

  void shortenPath(vector<Vector3d>& path);

public:
  typedef shared_ptr<FastExplorationManager> Ptr;
};

}  // namespace fast_planner

#endif
