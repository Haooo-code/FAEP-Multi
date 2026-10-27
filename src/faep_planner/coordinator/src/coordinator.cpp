/*
 * FAEP 多机扩展 —— 协调器 v1
 *
 * 职责：
 *   1) 汇聚各机前沿快照（/droneN/coord/frontier_snapshot，含位姿/状态/前沿簇摘要）
 *   2) 全局任务池：空间距离合并各机重复上报的簇，维护 认领机/租约/存活
 *   3) 分配：未认领任务按"最近 + 负载均衡"贪心分配，租约默认 60s，
 *      owner 持续观测到任务则自动续租；失联机任务全释放
 *   4) 下发：每机一份任务区域白名单（/droneN/coord/assignment，latched）
 *   5) 终止：所有机 FINISH 且任务池清空 -> /coord/halt；全局超时兜底
 *   6) 兜底：某机长时间无任务可分配 -> free_explore=true（放开单机过滤）
 *
 * 设计说明（v1 简化）：
 *   - 不做体素级地图共享，协调只用"前沿簇摘要"，带宽小、实现简单
 *   - 任务用空间区域（中心 + 半径）表达，单机按"前沿中心落入区域"过滤，
 *     不依赖跨机的稳定 ID（前沿会随探索漂移，位置谓词鲁棒）
 */
#include <ros/ros.h>
#include <coord_msgs/FrontierSnapshot.h>
#include <coord_msgs/FrontierAssignment.h>
#include <std_msgs/Bool.h>
#include <Eigen/Eigen>
#include <vector>
#include <string>
#include <algorithm>
#include <sstream>
#include <limits>

struct DroneInput
{
  int id;
  bool alive;
  ros::Time last_stamp;
  int state;  // 0=探索中 1=已完成 2=无前沿等待
  Eigen::Vector3d pos;
  std::vector<Eigen::Vector3d> centers;
  std::vector<float> sizes;
  // 卡住检测：位置长时间无变化（排除 FINISH 悬停）-> 释放任务，避免占用不下发
  Eigen::Vector3d last_progress_pos;
  ros::Time last_progress_time;
  bool stuck;
  ros::Time stuck_until;  // 卡住冷静期：期间不参与新任务分配（防止"释放->被同一机抢回"循环）

  DroneInput()
      : id(0), alive(false), state(2), pos(Eigen::Vector3d::Zero()),
        last_progress_pos(Eigen::Vector3d::Zero()), stuck(false)
  {
  }
};

struct Task
{
  int id;
  Eigen::Vector3d center;
  float radius;
  int owner;  // -1 = 未认领
  ros::Time lease_expire;
  ros::Time last_seen;
  ros::Time created;  // 创建时刻（超龄强制过期的基准）
  bool done;

  Task() : id(0), radius(2.0), owner(-1), done(false)
  {
  }
};

class Coordinator
{
public:
  explicit Coordinator(ros::NodeHandle &nh) : nh_(nh)
  {
  }

  void init()
  {
    nh_.param("drone_num", drone_num_, 3);
    nh_.param("merge_dist", merge_dist_, 1.5);
    nh_.param("task_radius", task_radius_, 2.0);
    nh_.param("lease_dur", lease_dur_, 60.0);
    nh_.param("task_lost_time", task_lost_time_, 8.0);
    nh_.param("status_timeout", status_timeout_, 10.0);
    nh_.param("tick_period", tick_period_, 0.2);
    nh_.param("load_weight", load_weight_, 8.0);
    nh_.param("free_wait_time", free_wait_time_, 20.0);
    nh_.param("global_timeout", global_timeout_, 900.0);
    nh_.param("stagnation_time", stagnation_time_, 180.0);
    nh_.param("task_max_age", task_max_age_, 150.0);
    // v2.0：空间分区（按各机初始位置沿离散度大的轴做 Voronoi 扇区）
    nh_.param("partition_mode", partition_mode_, false);
    // v2.1：等面积分区。分界由离线地图工具按自由区面积计算后显式传入，
    // 协调器只负责校验与执行，避免把地图解析耦合进任务层。
    nh_.param("equal_area_mode", equal_area_mode_, false);
    nh_.param("sector_axis", sector_axis_param_, -1);
    nh_.param("sector_bounds", sector_bounds_str_, std::string(""));
    nh_.param("recovery_grace", recovery_grace_, 20.0);
    nh_.param("recovery_timeout", recovery_timeout_, 150.0);

    drones_.resize(drone_num_);
    sub_snap_.resize(drone_num_);
    pub_asgn_.resize(drone_num_);
    last_asgn_hash_.resize(drone_num_, 0);
    free_explore_.resize(drone_num_, false);
    last_task_time_.resize(drone_num_);
    idle_since_.resize(drone_num_);
    idle_timer_on_.assign(drone_num_, false);
    sect_lo_.assign(drone_num_, -1e6);
    sect_hi_.assign(drone_num_, 1e6);

    for (int i = 0; i < drone_num_; ++i)
    {
      drones_[i].id = i + 1;
      std::string ns = "/drone" + std::to_string(i + 1);
      sub_snap_[i] = nh_.subscribe<coord_msgs::FrontierSnapshot>(
          ns + "/coord/frontier_snapshot", 10, boost::bind(&Coordinator::snapshotCallback, this, _1, i));
      pub_asgn_[i] =
          nh_.advertise<coord_msgs::FrontierAssignment>(ns + "/coord/assignment", 10, true);
    }
    pub_halt_ = nh_.advertise<std_msgs::Bool>("/coord/halt", 10, true);
    sub_start_ = nh_.subscribe("/coord/start", 10, &Coordinator::startCallback, this);

    ros::Time now = ros::Time::now();
    for (int i = 0; i < drone_num_; ++i)
      last_task_time_[i] = now;

    start_time_ = now;
    last_pool_change_ = now;
    timer_ = nh_.createTimer(ros::Duration(tick_period_), &Coordinator::tick, this);
    ROS_INFO("[coord] started: drone_num=%d, merge=%.1fm, lease=%.0fs, lost=%.0fs, timeout=%.0fs",
             drone_num_, merge_dist_, lease_dur_, task_lost_time_, global_timeout_);
  }

private:
  ros::NodeHandle nh_;
  int drone_num_;
  double merge_dist_, task_radius_, lease_dur_, task_lost_time_, status_timeout_;
  double tick_period_, load_weight_, free_wait_time_, global_timeout_;
  double stagnation_time_;  // 任务池停滞判定（无新任务且无完成超过该时长 -> 判定探索饱和）
  double task_max_age_;     // 任务超龄强制过期（保证任务池有限时间清空）

  std::vector<DroneInput> drones_;
  std::vector<ros::Subscriber> sub_snap_;
  std::vector<ros::Publisher> pub_asgn_;
  ros::Publisher pub_halt_;
  ros::Subscriber sub_start_;
  ros::Timer timer_;

  std::vector<Task> tasks_;
  int next_task_id_ = 0;
  int asgn_version_ = 0;
  bool halted_ = false;
  ros::Time start_time_;
  ros::Time last_pool_change_;
  bool any_drone_ever_explored_ = false;  // 至少有一台机进入过"探索中"（防启动期空窗误判收尾）
  std::vector<int> last_asgn_hash_;
  std::vector<bool> free_explore_;
  std::vector<ros::Time> last_task_time_;  // 每机最近一次"被分配到任务"的时间
  std::vector<ros::Time> idle_since_;      // v2.0：连续"等待分配"起始时刻（兜底自由探索计时）
  std::vector<bool> idle_timer_on_;        // v2.0：空闲计时器是否在走

  // ---- v2.0 空间分区 ----
  bool partition_mode_ = false;
  bool sectors_ready_ = false;
  int sector_axis_ = 0;                 // 0=x, 1=y（取各机初始位置离散度更大的轴）
  double sector_b0_ = 0.0, sector_b1_ = 0.0;  // 两条分界线（该轴坐标）
  std::vector<double> sect_lo_, sect_hi_;     // 每机扇区区间（按 drone 下标）
  int all_idle_ticks_ = 0;              // v2.0：所有机都不在探索的连续 tick 数（收尾兜底）
  bool equal_area_mode_ = false;        // v2.1：使用显式等面积分界
  int sector_axis_param_ = -1;          // v2.1：-1=自动选轴，0=x，1=y
  std::string sector_bounds_str_;       // v2.1：逗号分隔的 N-1 条分界
  bool degraded_mode_ = false;          // v2.1：有飞机失联，分区降级为全局探索
  bool degraded_sweep_started_ = false; // v2.1：任务级重派无效后，切到全局扫尾
  ros::Time degraded_since_;            // 降级起始时刻（给幸存机留恢复缓冲）
  double recovery_grace_ = 20.0;        // 降级后至少等待多久才允许“全空闲”收尾
  double recovery_timeout_ = 150.0;     // 降级恢复总时限（到点统一 HALT，覆盖可能不全）

  // 分区是否仍按扇区执行（失联后自动降级）
  bool partitionActive() const
  {
    return partition_mode_ && sectors_ready_ && !degraded_mode_;
  }

  // 解析逗号分隔的分界字符串
  bool parseSectorBounds(std::vector<double> &bounds) const
  {
    bounds.clear();
    std::stringstream ss(sector_bounds_str_);
    std::string item;
    while (std::getline(ss, item, ','))
    {
      if (item.empty())
        continue;
      try
      {
        bounds.push_back(std::stod(item));
      }
      catch (const std::exception &)
      {
        return false;
      }
    }
    return !bounds.empty();
  }

  // 计算扇区（首次所有机在线时调用一次）：按初始位置排序 + 取中点分界
  void initSectorsIfNeeded(const ros::Time &now)
  {
    if (!partition_mode_ || sectors_ready_)
      return;
    for (auto &d : drones_)
      if (!d.alive)
        return;  // 等所有机上线
    double sx = 1e9, sy = 1e9, bx = -1e9, by = -1e9;
    for (auto &d : drones_)
    {
      sx = std::min(sx, d.pos.x());
      bx = std::max(bx, d.pos.x());
      sy = std::min(sy, d.pos.y());
      by = std::max(by, d.pos.y());
    }
    sector_axis_ = (sector_axis_param_ == 0 || sector_axis_param_ == 1)
                       ? sector_axis_param_
                       : ((bx - sx >= by - sy) ? 0 : 1);
    std::vector<int> order(drone_num_);
    for (int i = 0; i < drone_num_; ++i)
      order[i] = i;
    std::sort(order.begin(), order.end(), [&](int a, int b) {
      return drones_[a].pos[sector_axis_] < drones_[b].pos[sector_axis_];
    });
    // 分界：默认取相邻初始位置的中点（Voronoi 一维划分）；
    // 等面积模式则读取离线工具算出的分界，并校验每架机的起点仍在自己的扇区内。
    std::vector<double> bounds;
    bool use_equal_area = equal_area_mode_;
    if (use_equal_area)
    {
      if (!parseSectorBounds(bounds) || int(bounds.size()) != drone_num_ - 1)
      {
        ROS_ERROR("[coord] equal_area_mode requires %d comma-separated sector bounds, got '%s'; "
                  "falling back to Voronoi",
                  drone_num_ - 1, sector_bounds_str_.c_str());
        use_equal_area = false;
      }
      else
      {
        for (int k = 0; k < int(bounds.size()); ++k)
        {
          double left = drones_[order[k]].pos[sector_axis_];
          double right = drones_[order[k + 1]].pos[sector_axis_];
          if (!(bounds[k] > left + 1e-6 && bounds[k] < right - 1e-6))
          {
            ROS_ERROR("[coord] sector bound %.2f is not between drone%d(%.2f) and drone%d(%.2f); "
                      "falling back to Voronoi",
                      bounds[k], order[k] + 1, left, order[k + 1] + 1, right);
            use_equal_area = false;
            break;
          }
        }
      }
    }

    if (use_equal_area)
    {
      sector_b0_ = bounds.size() > 0 ? bounds[0] : 0.0;
      sector_b1_ = bounds.size() > 1 ? bounds[1] : 0.0;
    }
    else
    {
      bounds.clear();
      for (int k = 0; k + 1 < drone_num_; ++k)
        bounds.push_back(0.5 * (drones_[order[k]].pos[sector_axis_] +
                                drones_[order[k + 1]].pos[sector_axis_]));
      sector_b0_ = bounds.size() > 0 ? bounds[0] : 0.0;
      sector_b1_ = bounds.size() > 1 ? bounds[1] : 0.0;
    }

    sect_lo_[order[0]] = -1e6;
    for (int k = 0; k + 1 < drone_num_; ++k)
    {
      sect_hi_[order[k]] = bounds[k];
      sect_lo_[order[k + 1]] = bounds[k];
    }
    sect_hi_[order[drone_num_ - 1]] = 1e6;
    sectors_ready_ = true;
    ROS_WARN("[coord] partition mode ON: mode=%s axis=%s boundaries=(%.2f, %.2f)",
             use_equal_area ? "equal_area" : "voronoi", sector_axis_ == 0 ? "x" : "y", sector_b0_,
             sector_b1_);
    for (int k = 0; k < drone_num_; ++k)
    {
      int i = order[k];
      ROS_WARN("[coord]   drone%d sector [%.2f, %.2f] start=%.2f", i + 1, sect_lo_[i], sect_hi_[i],
               drones_[i].pos[sector_axis_]);
    }
  }

  // 任务中心所属扇区的 owner（drone id）
  int ownerOfSector(const Eigen::Vector3d &c) const
  {
    double v = (sector_axis_ == 0) ? c.x() : c.y();
    for (int i = 0; i < drone_num_; ++i)
      if (v >= sect_lo_[i] && v <= sect_hi_[i])
        return drones_[i].id;
    return -1;
  }

  void snapshotCallback(const coord_msgs::FrontierSnapshotConstPtr &msg, int idx)
  {
    DroneInput &d = drones_[idx];
    bool first = !d.alive;
    d.alive = true;
    d.last_stamp = ros::Time::now();
    d.state = msg->state;
    d.pos << msg->pose.position.x, msg->pose.position.y, msg->pose.position.z;
    if (first || d.last_progress_time.isZero())
    {
      d.last_progress_pos = d.pos;
      d.last_progress_time = ros::Time::now();
    }
    d.centers.clear();
    d.sizes.clear();
    for (size_t i = 0; i < msg->centers.size(); ++i)
    {
      d.centers.push_back(Eigen::Vector3d(msg->centers[i].x, msg->centers[i].y, msg->centers[i].z));
      d.sizes.push_back(i < msg->sizes.size() ? msg->sizes[i] : 100.0f);
    }
  }

  void startCallback(const std_msgs::BoolConstPtr &msg)
  {
    (void)msg;
    start_time_ = ros::Time::now();
    halted_ = false;
    ROS_INFO("[coord] start signal received");
  }

  // 查找距离 c 最近的未完成任务（< merge_dist），返回索引；-1=没有
  int findTaskNear(const Eigen::Vector3d &c)
  {
    int best = -1;
    double best_d = merge_dist_;
    for (size_t k = 0; k < tasks_.size(); ++k)
    {
      if (tasks_[k].done)
        continue;
      double d = (tasks_[k].center - c).norm();
      if (d < best_d)
      {
        best_d = d;
        best = int(k);
      }
    }
    return best;
  }

  void tick(const ros::TimerEvent &e)
  {
    (void)e;
    if (halted_)
      return;
    ros::Time now = ros::Time::now();
    initSectorsIfNeeded(now);

    // 1) 存活检查：失联机释放全部任务（兜底：其它机可以接手）
    for (auto &d : drones_)
    {
      if (d.alive && d.state == 0)
        any_drone_ever_explored_ = true;
      if (d.alive && (now - d.last_stamp).toSec() > status_timeout_)
      {
        d.alive = false;
        int released_on_loss = 0;
        for (auto &t : tasks_)
          if (!t.done && t.owner == d.id)
          {
            t.owner = -1;
            ++released_on_loss;
          }
        ROS_WARN("[coord] drone%d lost (>%.0fs), released %d task(s)", d.id, status_timeout_,
                 released_on_loss);

        // v2.1 故障降级：分区模式下 owner 失联后不能再把任务派回空扇区。
        // 关闭扇区过滤，让幸存机可以全局探索；并给它们一个恢复缓冲期，
        // 避免刚失联时的短暂等待被误判为“全部空闲”而提前 HALT。
        if (partition_mode_ && sectors_ready_ && !degraded_mode_)
        {
          int alive_after = 0;
          for (auto &x : drones_)
            if (x.alive)
              ++alive_after;
          if (alive_after > 0)
          {
            degraded_mode_ = true;
            degraded_since_ = now;
            for (auto &t : tasks_)
              if (!t.done)
                t.owner = -1;
            last_pool_change_ = now;
            ROS_WARN("[coord] partition degraded: drone%d lost, %d survivor(s) take over tasks first",
                     d.id, alive_after);
          }
        }
      }
    }

    // 1b) 卡住检测：探索中（state=0）但位置 30s 内位移 < 0.8m -> 判定卡住，释放其任务
    //     （单机侧的失败目标黑名单自愈会尝试脱困；任务释放后其它机可以接手）
    for (auto &d : drones_)
    {
      if (!d.alive)
        continue;
      if ((d.pos - d.last_progress_pos).norm() > 0.8)
      {
        d.last_progress_pos = d.pos;
        d.last_progress_time = now;
        d.stuck = false;
      }
      else if (!d.stuck && d.state == 0 && !d.last_progress_time.isZero() &&
               (now - d.last_progress_time).toSec() > 30.0)
      {
        d.stuck = true;
        d.stuck_until = now + ros::Duration(60.0);  // 冷静期 60s：期间不参与分配
        int released = 0;
        for (auto &t : tasks_)
          if (!t.done && t.owner == d.id)
          {
            t.owner = -1;
            ++released;
          }
        ROS_WARN("[coord] drone%d appears stuck (no progress >30s), released %d task(s), cooldown 60s",
                 d.id, released);
      }
    }

    // 2) 合并任务池
    for (auto &d : drones_)
    {
      if (!d.alive)
        continue;
      if (d.state == 1)
        continue;  // v1.2：FINISH 机快照中残留的前沿（不可达/已放弃）不再喂任务，避免任务永不关闭
      for (size_t k = 0; k < d.centers.size(); ++k)
      {
        int ti = findTaskNear(d.centers[k]);
        if (ti >= 0)
        {
          tasks_[ti].last_seen = now;
          // 平滑中心（前沿会随探索缓慢移动，避免任务区域跳动）
          tasks_[ti].center = 0.7 * tasks_[ti].center + 0.3 * d.centers[k];
        }
        else
        {
          Task t;
          t.id = next_task_id_++;
          t.center = d.centers[k];
          t.radius = float(task_radius_);
          // v2.0：分区模式下任务在创建时就归所属扇区的机（不再按最近机重派）
          t.owner = partitionActive() ? ownerOfSector(t.center) : -1;
          t.lease_expire = now;
          t.last_seen = now;
          t.created = now;
          tasks_.push_back(t);
          last_pool_change_ = now;
          ROS_INFO("[coord] new task #%d from drone%d at (%.1f, %.1f, %.1f)", t.id, d.id, t.center.x(),
                   t.center.y(), t.center.z());
        }
      }
    }

    // 3) 完成判定：长时间没有被任何机观测到 -> 视为完成/失效
    for (auto &t : tasks_)
    {
      if (!t.done && (now - t.last_seen).toSec() > task_lost_time_)
      {
        t.done = true;
        last_pool_change_ = now;
        int done_cnt = 0;
        for (auto &x : tasks_)
          if (x.done)
            ++done_cnt;
        ROS_INFO("[coord] task #%d gone -> done (%d done total)", t.id, done_cnt);
      }
    }

    // 3b) 超龄过期（v1.5）：任务存活超过 task_max_age_ 仍未收场 -> 强制过期。
    //     保证任务池在任何情况下都能在有限时间内清空（解决"个别前沿长期滞留
    //     导致 halt 永远不满足"的收尾僵局）。
    for (auto &t : tasks_)
    {
      if (!t.done && (now - t.created).toSec() > task_max_age_)
      {
        t.done = true;
        last_pool_change_ = now;
        ROS_WARN("[coord] task #%d expired (age > %.0fs), forced done", t.id, task_max_age_);
      }
    }

    // 4) 租约：owner 仍在观测 -> 续租；租约到期且不再观测 -> 释放
    for (auto &t : tasks_)
    {
      if (t.done || t.owner == -1)
        continue;
      DroneInput &d = drones_[t.owner - 1];
      bool owner_sees = false;
      if (d.alive)
      {
        for (auto &c : d.centers)
          if ((c - t.center).norm() < merge_dist_ * 1.5)
          {
            owner_sees = true;
            break;
          }
      }
      if (owner_sees)
        t.lease_expire = now + ros::Duration(lease_dur_);
      else if (!partitionActive() && !degraded_mode_ && d.state == 2)
      {
        // v1.2：owner 处于"等待分配"（本地无活可做）且不再观测该任务 -> 立即释放，
        // 避免任务滞留在等待机名下直到租约到期（会拖慢全局终止）。
        // 故障降级期间不立即释放：否则等待机每 tick 释放→重派，任务反复抖动。
        ROS_WARN("[coord] task #%d released (owner drone%d idle)", t.id, t.owner);
        t.owner = -1;
      }
      else if (now > t.lease_expire)
      {
        ROS_WARN("[coord] task #%d lease expired, releasing (owner drone%d)", t.id, t.owner);
        t.owner = -1;
      }
    }

    // 5) 分配未认领任务：cost = 距离 + 负载惩罚
    for (auto &t : tasks_)
    {
      if (t.done || t.owner != -1)
        continue;
      if (partitionActive())
      {
        // v2.0 分区模式：任务只派给所属扇区的机（不按距离抢单，避免散装与重派）
        int owner = ownerOfSector(t.center);
        if (owner > 0 && drones_[owner - 1].alive)
        {
          t.owner = owner;
          t.lease_expire = now + ros::Duration(lease_dur_);
        }
        continue;
      }
      int best = -1;
      double best_cost = 1e18;
      for (auto &d : drones_)
      {
        if (!d.alive)
          continue;
        if (now < d.stuck_until)  // 卡住冷静期内不参与分配
          continue;
        if (free_explore_[d.id - 1])  // v2.0：已进入自由探索的机不再接收区域任务
          continue;
        int load = 0;
        for (auto &t2 : tasks_)
          if (!t2.done && t2.owner == d.id)
            ++load;
        double cost = (d.pos - t.center).norm() + load_weight_ * load;
        if (cost < best_cost)
        {
          best_cost = cost;
          best = d.id;
        }
      }
      if (best > 0)
      {
        t.owner = best;
        t.lease_expire = now + ros::Duration(lease_dur_);
        last_task_time_[best - 1] = now;
        ROS_INFO("[coord] assign task #%d -> drone%d (cost=%.1f, dist=%.1f)", t.id, best, best_cost,
                 (drones_[best - 1].pos - t.center).norm());
      }
    }

    // 5b) 故障降级后的两阶段恢复：先让幸存机按任务区域接手（可留下任务级重派日志）；
    //     若恢复缓冲期后仍无任务可做或没有任何幸存机在探索，再切全局自由扫尾。
    if (degraded_mode_ && !degraded_sweep_started_ &&
        (now - degraded_since_).toSec() > recovery_grace_)
    {
      bool active_task = false;
      for (auto &t : tasks_)
        if (!t.done)
          active_task = true;
      bool survivor_exploring = false;
      for (auto &d : drones_)
        if (d.alive && d.state == 0 && !d.stuck)
          survivor_exploring = true;
      if (!active_task || !survivor_exploring)
      {
        degraded_sweep_started_ = true;
        for (int i = 0; i < drone_num_; ++i)
          if (drones_[i].alive)
            free_explore_[i] = true;
        ROS_WARN("[coord] recovery: no task-level progress after %.0fs, survivors switch to global sweep",
                 recovery_grace_);
      }
    }

    // 6) 兜底自由探索（v2.0 修复）：以"连续处于等待分配（state=2）的时长"为准。
    //    旧逻辑按"名下无任务"计时，但等待机的任务每 tick 被"释放→重派"（保留给最近机），
    //    计时器被反复复位 -> free_explore 永不触发（office2 C 实测整轮 0 次），
    //    等待机长期悬停、拉长完成时间。修复：连续空闲超过 free_wait_time_ -> 打开
    //    自由探索（并交还名下任务），此后保持自主探索直到 halt，不再接收区域任务。
    //    注意：分区模式下不启用（每机只负责本扇区；空闲=本扇区已清完，应等待收尾）。
    for (int i = 0; i < drone_num_ && !partition_mode_; ++i)
    {
      DroneInput &d = drones_[i];
      if (!d.alive)
        continue;
      if (d.state == 2)
      {
        if (!idle_timer_on_[i])
        {
          idle_since_[i] = now;
          idle_timer_on_[i] = true;
        }
        else if (!free_explore_[i] && (now - idle_since_[i]).toSec() > free_wait_time_)
        {
          free_explore_[i] = true;
          int released = 0;
          for (auto &t : tasks_)
            if (!t.done && t.owner == d.id)
            {
              t.owner = -1;
              ++released;
            }
          ROS_WARN("[coord] drone%d idle for %.0fs -> free_explore ON (released %d task(s))",
                   d.id, free_wait_time_, released);
        }
      }
      else
      {
        idle_timer_on_[i] = false;
      }
    }

    // 7) 下发（内容变化才发）
    publishAssignments(false);

    // 8) 终止判定
    {
      int alive_cnt = 0;
      bool all_alive_finish = true;
      for (auto &d : drones_)
      {
        if (!d.alive)
          continue;
        ++alive_cnt;
        if (d.state != 1)
          all_alive_finish = false;
      }
      bool any_active = false;
      for (auto &t : tasks_)
        if (!t.done)
          any_active = true;
      bool any_exploring = false;
      for (auto &d : drones_)
        if (d.alive && d.state == 0 && !d.stuck)
          any_exploring = true;
      // v2.0：所有机都不探索（等待/完成）-> 没人还能推进，计数；连续 6s 直接收尾。
      // 解决"扇区内不可达前沿任务持续刷新 last_seen、拖到 150s 超龄才收尾"的长尾。
      // v2.1：失联机不参与“活着但未完成”的判定，否则 alive_cnt == drone_num_ 永远不成立。
      if (alive_cnt > 0 && !any_exploring && any_drone_ever_explored_)
        ++all_idle_ticks_;
      else
        all_idle_ticks_ = 0;
      bool recovery_ready = degraded_since_.isZero() ||
                            (now - degraded_since_).toSec() > recovery_grace_;
      if (alive_cnt > 0 && all_alive_finish && !any_active)
        halt("all alive drones finished, task pool empty");
      else if (all_idle_ticks_ > 30 && recovery_ready)  // 6s @ 0.2s
        halt("all drones idle (no exploring) for >6s");
      else if (any_drone_ever_explored_ && next_task_id_ > 0 && !any_active && !any_exploring &&
               recovery_ready)
        // v1.2：任务池已空且没有任何机在探索（完成/等待）-> 立即收尾，
        // 不等待"全部 FINISH"（协调模式下"等待"中的机不会自行 FINISH）
        halt("no active task and no drone exploring");
      else if (!tasks_.empty() && any_active &&
               (now - last_pool_change_).toSec() > stagnation_time_)
        halt("stagnation: task pool unchanged for >" + std::to_string(int(stagnation_time_)) + "s");
      else if (degraded_mode_ && (now - degraded_since_).toSec() > recovery_timeout_)
        halt("degraded recovery timeout (coverage may be incomplete)");
      else if ((now - start_time_).toSec() > global_timeout_)
        halt("global timeout");
    }
  }

  void publishAssignments(bool force)
  {
    for (int i = 0; i < drone_num_; ++i)
    {
      DroneInput &d = drones_[i];
      std::vector<int> my;
      for (size_t k = 0; k < tasks_.size(); ++k)
        if (!tasks_[k].done && tasks_[k].owner == d.id)
          my.push_back(int(k));

      // 位置量化到 0.25m 粒度再入 hash：任务中心每 tick 都有微小平滑更新，
      // 若用全精度入 hash 会导致每次 tick 都判定"变化"而重复广播（实测 v 号每秒涨 5+）
      auto q = [](double v, double s) { return size_t(int(v * s) + 100000); };
      size_t h = my.size() * 131 + (free_explore_[i] ? 977 : 0);
      for (auto k : my)
        h = h * 37991 + q(tasks_[k].center.x(), 4.0) + q(tasks_[k].center.y(), 3.0) +
            q(tasks_[k].center.z(), 2.0) + tasks_[k].id;
      if (!force && h == last_asgn_hash_[i])
        continue;
      last_asgn_hash_[i] = h;

      coord_msgs::FrontierAssignment m;
      m.header.stamp = ros::Time::now();
      m.version = ++asgn_version_;
      // 降级后幸存机全局探索；分区标志关闭后，单机不再用扇区过滤前沿。
      m.free_explore = (degraded_mode_ && degraded_sweep_started_ && d.alive) ? true : free_explore_[i];
      m.partition = partitionActive();
      m.sector_axis = sector_axis_;
      m.sector_lo = float(sect_lo_[i]);
      m.sector_hi = float(sect_hi_[i]);
      m.centers.resize(my.size());
      m.radii.resize(my.size());
      for (size_t j = 0; j < my.size(); ++j)
      {
        Task &t = tasks_[my[j]];
        m.centers[j].x = t.center.x();
        m.centers[j].y = t.center.y();
        m.centers[j].z = t.center.z();
        m.radii[j] = t.radius;
      }
      pub_asgn_[i].publish(m);
      ROS_INFO("[coord] send drone%d: %zu task regions (v%d, free=%d)", d.id, my.size(), m.version,
               int(m.free_explore));
    }
  }

  void halt(const std::string &reason)
  {
    halted_ = true;
    std_msgs::Bool m;
    m.data = true;
    pub_halt_.publish(m);
    ROS_INFO("[coord] ============ HALT: %s ============", reason.c_str());
  }
};

int main(int argc, char **argv)
{
  ros::init(argc, argv, "faep_coordinator");
  ros::NodeHandle nh("~");
  Coordinator coord(nh);
  coord.init();
  ros::spin();
  return 0;
}
