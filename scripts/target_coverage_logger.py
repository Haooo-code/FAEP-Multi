#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""记录目标确认瞬间和最终 HALT 时的三机轨迹投影覆盖率。"""

import argparse
import json
import os
import threading

import numpy as np
import rospy
from nav_msgs.msg import Odometry
from std_msgs.msg import Bool

from coord_msgs.msg import TargetStatus


STATE_NAMES = {
    TargetStatus.SEARCHING: "SEARCHING",
    TargetStatus.CANDIDATE: "CANDIDATE",
    TargetStatus.VERIFYING: "VERIFYING",
    TargetStatus.CONFIRMED: "CONFIRMED",
    TargetStatus.NOT_FOUND: "NOT_FOUND",
}


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--pcd", required=True)
    parser.add_argument("--grid", type=float, default=1.0)
    parser.add_argument("--radius", type=float, default=1.0)
    return parser.parse_args(rospy.myargv()[1:])


def load_free_cells(pcd_path, grid_size):
    points_x = []
    points_y = []
    with open(pcd_path, encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if not line or line[0] in "#VSCWHPD":
                continue
            values = line.split()
            if len(values) != 3:
                continue
            points_x.append(float(values[0]))
            points_y.append(float(values[1]))

    xs = np.asarray(points_x)
    ys = np.asarray(points_y)
    x_min, x_max = int(np.floor(xs.min())), int(np.ceil(xs.max()))
    y_min, y_max = int(np.floor(ys.min())), int(np.ceil(ys.max()))

    occupied = {
        (int(np.floor(x / grid_size)), int(np.floor(y / grid_size)))
        for x, y in zip(xs, ys)
    }
    free = {
        (gx, gy)
        for gx in range(x_min, x_max + 1)
        for gy in range(y_min, y_max + 1)
        if (gx, gy) not in occupied
    }
    return free


class TargetCoverageLogger:
    def __init__(self, args):
        self.args = args
        self.lock = threading.Lock()
        self.free = load_free_cells(args.pcd, args.grid)
        self.radius_cells = int(round(args.radius / args.grid))
        self.positions = {}
        self.tracks = {1: set(), 2: set(), 3: set()}
        self.status_snapshot = None
        self.halt_snapshot = None
        self.start_time = rospy.Time.now()
        self.last_write = None

        for drone_id in (1, 2, 3):
            rospy.Subscriber(
                f"/drone{drone_id}/state_ukf/odom",
                Odometry,
                self.odom_callback,
                callback_args=drone_id,
                queue_size=10,
            )
        rospy.Subscriber("/target/status", TargetStatus, self.status_callback, queue_size=10)
        rospy.Subscriber("/coord/halt", Bool, self.halt_callback, queue_size=10)
        rospy.Timer(rospy.Duration(1.0), self.write_callback)
        rospy.on_shutdown(self.write)

    def odom_callback(self, msg, drone_id):
        position = msg.pose.pose.position
        cell = (int(np.floor(position.x / self.args.grid)),
                int(np.floor(position.y / self.args.grid)))
        with self.lock:
            if self.positions.get(drone_id) == cell:
                return
            self.positions[drone_id] = cell
            for dx in range(-self.radius_cells, self.radius_cells + 1):
                for dy in range(-self.radius_cells, self.radius_cells + 1):
                    candidate = (cell[0] + dx, cell[1] + dy)
                    if candidate in self.free:
                        self.tracks[drone_id].add(candidate)

    def coverage(self):
        union = self.tracks[1] | self.tracks[2] | self.tracks[3]
        multi = (
            (self.tracks[1] & self.tracks[2])
            | (self.tracks[1] & self.tracks[3])
            | (self.tracks[2] & self.tracks[3])
        )
        free_count = max(1, len(self.free))
        union_count = len(union)
        return {
            "time_from_start_s": round((rospy.Time.now() - self.start_time).to_sec(), 2),
            "free_cells": len(self.free),
            "drone_cells": {
                "drone1": len(self.tracks[1]),
                "drone2": len(self.tracks[2]),
                "drone3": len(self.tracks[3]),
            },
            "union_cells": union_count,
            "union_coverage_pct": round(100.0 * union_count / free_count, 2),
            "multi_cells": len(multi),
            "multi_pct_of_union": round(100.0 * len(multi) / max(1, union_count), 2),
        }

    def status_callback(self, msg):
        if msg.state not in (TargetStatus.CONFIRMED, TargetStatus.NOT_FOUND):
            return
        with self.lock:
            self.status_snapshot = self.coverage()
            self.status_snapshot["state"] = STATE_NAMES.get(msg.state, str(msg.state))
            self.status_snapshot["source_id"] = int(msg.source_id)
        self.write()

    def halt_callback(self, msg):
        if not msg.data:
            return
        with self.lock:
            if self.halt_snapshot is None:
                self.halt_snapshot = self.coverage()
        self.write()
        rospy.Timer(rospy.Duration(1.0), lambda _: rospy.signal_shutdown("halt recorded"), oneshot=True)

    def write_callback(self, _event):
        self.write()

    def write(self):
        with self.lock:
            payload = {
                "map_pcd": os.path.basename(self.args.pcd),
                "grid_m": self.args.grid,
                "radius_m": self.args.radius,
                "status_coverage": self.status_snapshot,
                "halt_coverage": self.halt_snapshot,
                "current_coverage": self.coverage(),
            }
            text = json.dumps(payload, ensure_ascii=False, indent=2)
            temporary = self.args.output + ".tmp"
            with open(temporary, "w", encoding="utf-8") as handle:
                handle.write(text)
            os.replace(temporary, self.args.output)
            self.last_write = rospy.Time.now()


def main():
    rospy.init_node("target_coverage_logger", anonymous=True)
    args = parse_args()
    output_dir = os.path.dirname(args.output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    TargetCoverageLogger(args)
    rospy.spin()


if __name__ == "__main__":
    main()
