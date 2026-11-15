#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""累积三机轨迹并可选发布扇区分界，供 RViz 录制使用。"""

import argparse

import rospy
from geometry_msgs.msg import Point
from nav_msgs.msg import Odometry
from visualization_msgs.msg import Marker, MarkerArray


COLORS = {
    1: (0.12, 0.47, 0.71),
    2: (1.0, 0.50, 0.05),
    3: (0.17, 0.63, 0.17),
}


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sectors", action="store_true")
    parser.add_argument("--bounds", default="-5.5,0.5")
    parser.add_argument("--y-min", type=float, default=-9.9)
    parser.add_argument("--y-max", type=float, default=9.9)
    return parser.parse_args(rospy.myargv()[1:])


def line_marker(marker_id, points, color, width=0.10, z=0.08):
    marker = Marker()
    marker.header.frame_id = "world"
    marker.ns = "trails"
    marker.id = marker_id
    marker.type = Marker.LINE_STRIP
    marker.action = Marker.ADD
    marker.scale.x = width
    marker.color.r = color[0]
    marker.color.g = color[1]
    marker.color.b = color[2]
    marker.color.a = 1.0
    marker.pose.orientation.w = 1.0
    for x, y in points:
        marker.points.append(Point(x=x, y=y, z=z))
    return marker


def main():
    args = parse_args()
    sector_bounds = [float(value) for value in args.bounds.split(",") if value]
    trails = {1: [], 2: [], 3: []}

    rospy.init_node("multi_trail_pub", anonymous=True)

    def make_callback(drone_id):
        def callback(msg):
            position = msg.pose.pose.position
            points = trails[drone_id]
            if not points or abs(position.x - points[-1][0]) + abs(position.y - points[-1][1]) > 0.15:
                points.append((position.x, position.y))
            if len(points) > 6000:
                del points[:1000]

        return callback

    for drone_id in (1, 2, 3):
        rospy.Subscriber(
            f"/drone{drone_id}/state_ukf/odom",
            Odometry,
            make_callback(drone_id),
            queue_size=10,
        )

    publisher = rospy.Publisher("/multi_trails", MarkerArray, queue_size=5)
    rate = rospy.Rate(5)
    while not rospy.is_shutdown():
        markers = MarkerArray()
        markers.markers.append(Marker(action=Marker.DELETEALL))
        for drone_id in (1, 2, 3):
            if len(trails[drone_id]) >= 2:
                markers.markers.append(
                    line_marker(drone_id, trails[drone_id], COLORS[drone_id], width=0.11)
                )
        if args.sectors:
            for index, x in enumerate(sector_bounds):
                markers.markers.append(
                    line_marker(
                        10 + index,
                        [(x, args.y_min), (x, args.y_max)],
                        (0.08, 0.10, 0.14),
                        width=0.12,
                        z=0.25,
                    )
                )
        publisher.publish(markers)
        rate.sleep()


if __name__ == "__main__":
    main()
