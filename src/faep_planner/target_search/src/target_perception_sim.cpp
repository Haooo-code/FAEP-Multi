/*
 * 模拟目标感知节点
 *
 * 仿真器内部知道目标真值，但规划器不能直接读取目标坐标。本节点使用相机位姿、
 * 深度图、视场、距离和遮挡生成带噪声的检测结果，规划器只接收 TargetDetection。
 */

#include <algorithm>
#include <cmath>
#include <random>
#include <vector>

#include <Eigen/Eigen>
#include <cv_bridge/cv_bridge.h>
#include <geometry_msgs/PoseStamped.h>
#include <opencv2/opencv.hpp>
#include <ros/ros.h>
#include <sensor_msgs/Image.h>

#include <coord_msgs/TargetDetection.h>

class TargetPerceptionSim
{
public:
  TargetPerceptionSim() : nh_(), pnh_("~"), rng_(1)
  {
  }

  void init()
  {
    pnh_.param("source_id", source_id_, 1);
    pnh_.param("target_present", target_present_, true);
    pnh_.param("target_class", target_class_, std::string("person"));
    pnh_.param("target_x", target_(0), 5.0);
    pnh_.param("target_y", target_(1), 5.0);
    pnh_.param("target_z", target_(2), 1.0);

    pnh_.param("camera/fx", fx_, 387.229248046875);
    pnh_.param("camera/fy", fy_, 387.229248046875);
    pnh_.param("camera/cx", cx_, 321.04638671875);
    pnh_.param("camera/cy", cy_, 243.44969177246094);

    pnh_.param("sensing/min_range", min_range_, 0.6);
    pnh_.param("sensing/max_range", max_range_, 7.0);
    pnh_.param("sensing/fov_margin_px", fov_margin_px_, 8);
    pnh_.param("sensing/occlusion_tolerance", occlusion_tolerance_, 0.45);
    pnh_.param("sensing/base_detection_probability", base_detection_probability_, 0.92);
    pnh_.param("sensing/position_noise", position_noise_, 0.08);
    pnh_.param("sensing/confidence_noise", confidence_noise_, 0.03);
    pnh_.param("sensing/verification_confidence", verification_confidence_, 0.80);
    pnh_.param("sensing/publish_rate", publish_rate_, 5.0);

    int seed = 0;
    pnh_.param("sensing/random_seed", seed, source_id_ * 7919);
    rng_.seed(static_cast<unsigned int>(seed));

    detection_pub_ =
        nh_.advertise<coord_msgs::TargetDetection>("/target/detection", 20);
    pose_sub_ = nh_.subscribe("sensor_pose", 10, &TargetPerceptionSim::poseCallback, this);
    depth_sub_ = nh_.subscribe("depth", 5, &TargetPerceptionSim::depthCallback, this);

    const double period = 1.0 / std::max(1.0, publish_rate_);
    timer_ = nh_.createTimer(ros::Duration(period), &TargetPerceptionSim::timerCallback, this);

    ROS_INFO("[target_perception_sim] drone%d enabled, truth=(%.2f, %.2f, %.2f)",
             source_id_, target_.x(), target_.y(), target_.z());
  }

private:
  void poseCallback(const geometry_msgs::PoseStampedConstPtr &msg)
  {
    latest_pose_ = *msg;
    has_pose_ = true;
  }

  void depthCallback(const sensor_msgs::ImageConstPtr &msg)
  {
    try
    {
      cv_bridge::CvImageConstPtr cv_ptr =
          cv_bridge::toCvCopy(msg, sensor_msgs::image_encodings::TYPE_32FC1);
      depth_ = cv_ptr->image.clone();
      latest_depth_stamp_ = msg->header.stamp;
      has_depth_ = true;
    }
    catch (const cv_bridge::Exception &e)
    {
      ROS_WARN_THROTTLE(5.0, "[target_perception_sim] depth conversion failed: %s", e.what());
    }
  }

  double medianDepthNear(int u, int v) const
  {
    std::vector<float> values;
    for (int dy = -1; dy <= 1; ++dy)
    {
      for (int dx = -1; dx <= 1; ++dx)
      {
        const int uu = u + dx;
        const int vv = v + dy;
        if (uu < 0 || vv < 0 || uu >= depth_.cols || vv >= depth_.rows)
          continue;
        const float d = depth_.at<float>(vv, uu);
        if (std::isfinite(d) && d > 0.0f)
          values.push_back(d);
      }
    }
    if (values.empty())
      return 0.0;
    std::sort(values.begin(), values.end());
    return values[values.size() / 2];
  }

  void timerCallback(const ros::TimerEvent &)
  {
    if (!target_present_ || !has_pose_ || !has_depth_)
      return;

    const ros::Time now = ros::Time::now();
    if (!latest_pose_.header.stamp.isZero() && (now - latest_pose_.header.stamp).toSec() > 0.5)
      return;
    if (!latest_depth_stamp_.isZero() && (now - latest_depth_stamp_).toSec() > 0.5)
      return;
    if (!last_publish_.isZero() && (now - last_publish_).toSec() < 1.0 / publish_rate_)
      return;

    const geometry_msgs::Pose &pose = latest_pose_.pose;
    Eigen::Quaterniond q(pose.orientation.w, pose.orientation.x, pose.orientation.y,
                         pose.orientation.z);
    if (q.norm() < 1e-6)
      return;
    q.normalize();
    const Eigen::Vector3d camera_pos(pose.position.x, pose.position.y, pose.position.z);
    const Eigen::Vector3d p_cam = q.inverse() * (target_ - camera_pos);

    if (p_cam.z() < min_range_ || p_cam.z() > max_range_)
      return;

    const double range = p_cam.norm();
    if (range < min_range_ || range > max_range_)
      return;

    const double uf = fx_ * p_cam.x() / p_cam.z() + cx_;
    const double vf = fy_ * p_cam.y() / p_cam.z() + cy_;
    const int u = static_cast<int>(std::round(uf));
    const int v = static_cast<int>(std::round(vf));
    if (u < fov_margin_px_ || v < fov_margin_px_ || u >= depth_.cols - fov_margin_px_ ||
        v >= depth_.rows - fov_margin_px_)
      return;

    const double foreground_depth = medianDepthNear(u, v);
    if (foreground_depth > 0.0 && foreground_depth < p_cam.z() - occlusion_tolerance_)
      return;

    const double center_x = depth_.cols * 0.5;
    const double center_y = depth_.rows * 0.5;
    const double edge_ratio =
        std::max(std::abs(uf - center_x) / center_x, std::abs(vf - center_y) / center_y);
    const double range_ratio =
        std::max(0.0, std::min(1.0, (range - min_range_) / (max_range_ - min_range_)));

    double detection_probability =
        base_detection_probability_ * (1.0 - 0.28 * range_ratio - 0.22 * edge_ratio);
    detection_probability =
        std::max(0.20, std::min(base_detection_probability_, detection_probability));
    std::bernoulli_distribution detect(detection_probability);
    if (!detect(rng_))
      return;

    std::normal_distribution<double> confidence_noise(0.0, confidence_noise_);
    double confidence = 0.98 - 0.30 * range_ratio - 0.16 * edge_ratio +
                        confidence_noise(rng_);
    confidence = std::max(0.35, std::min(0.99, confidence));

    std::normal_distribution<double> position_noise(0.0, position_noise_);
    Eigen::Vector3d estimate = target_;
    estimate.x() += position_noise(rng_);
    estimate.y() += position_noise(rng_);
    estimate.z() += position_noise(rng_);

    coord_msgs::TargetDetection msg;
    msg.header.stamp = latest_pose_.header.stamp.isZero() ? now : latest_pose_.header.stamp;
    msg.header.frame_id = "world";
    msg.source_id = static_cast<uint8_t>(source_id_);
    msg.target_class = target_class_;
    msg.confidence = static_cast<float>(confidence);
    msg.position.x = estimate.x();
    msg.position.y = estimate.y();
    msg.position.z = estimate.z();
    msg.requires_verification = confidence < verification_confidence_;
    detection_pub_.publish(msg);
    last_publish_ = now;

    ROS_INFO_THROTTLE(1.0,
                      "[target_perception_sim] drone%d candidate confidence=%.2f "
                      "truth_range=%.2f verify=%s",
                      source_id_, confidence, range,
                      msg.requires_verification ? "yes" : "no");
  }

  ros::NodeHandle nh_;
  ros::NodeHandle pnh_;
  ros::Subscriber pose_sub_;
  ros::Subscriber depth_sub_;
  ros::Publisher detection_pub_;
  ros::Timer timer_;

  int source_id_ = 1;
  bool target_present_ = true;
  std::string target_class_ = "person";
  Eigen::Vector3d target_ = Eigen::Vector3d(5.0, 5.0, 1.0);

  double fx_ = 387.229248046875;
  double fy_ = 387.229248046875;
  double cx_ = 321.04638671875;
  double cy_ = 243.44969177246094;
  double min_range_ = 0.6;
  double max_range_ = 7.0;
  int fov_margin_px_ = 8;
  double occlusion_tolerance_ = 0.45;
  double base_detection_probability_ = 0.92;
  double position_noise_ = 0.08;
  double confidence_noise_ = 0.03;
  double verification_confidence_ = 0.80;
  double publish_rate_ = 5.0;

  geometry_msgs::PoseStamped latest_pose_;
  ros::Time latest_depth_stamp_;
  cv::Mat depth_;
  bool has_pose_ = false;
  bool has_depth_ = false;
  ros::Time last_publish_;
  std::mt19937 rng_;
};

int main(int argc, char **argv)
{
  ros::init(argc, argv, "target_perception_sim");
  TargetPerceptionSim node;
  node.init();
  ros::spin();
  return 0;
}
