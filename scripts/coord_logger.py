#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 多机实验数据记录：5Hz 记录三机位置到 CSV（用于最小机间距、轨迹分析）
import sys
import time
import csv
import rospy
from nav_msgs.msg import Odometry

out = sys.argv[1] if len(sys.argv) > 1 else '/mnt/d/WSL/exp_track.csv'
file = open(out, 'w')
writer = csv.writer(file)
writer.writerow(['t', 'd1x', 'd1y', 'd1z', 'd2x', 'd2y', 'd2z', 'd3x', 'd3y', 'd3z'])
state = {}


def make_cb(i):
    def cb(msg):
        p = msg.pose.pose.position
        state[i] = (p.x, p.y, p.z)
    return cb


rospy.init_node('coord_logger', anonymous=True)
for idx in (1, 2, 3):
    rospy.Subscriber('/drone%d/state_ukf/odom' % idx, Odometry, make_cb(idx))

r = rospy.Rate(5)
t0 = time.time()
while not rospy.is_shutdown():
    if len(state) >= 3:
        row = [round(time.time() - t0, 2)]
        for idx in (1, 2, 3):
            x, y, z = state[idx]
            row += [round(x, 3), round(y, 3), round(z, 3)]
        writer.writerow(row)
    r.sleep()
file.close()
