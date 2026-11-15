#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从目标搜索 RViz 配置生成带地图、障碍物和 FOV 的录像配置。"""

import copy
import os

import yaml


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_PATH = os.path.join(ROOT, "src", "faep_planner", "plan_manage", "config", "target_search.rviz")
OUT_DIR = os.path.join(ROOT, "src", "faep_planner", "exploration_manager", "config")

DRONE_COLORS = {
    1: "31; 119; 180",
    2: "255; 127; 14",
    3: "44; 160; 44",
}


def flatten(displays):
    result = []
    for display in displays:
        result.append(display)
        result.extend(flatten(display.get("Displays", [])))
    return result


def find_display(displays, name):
    for display in flatten(displays):
        if display.get("Name") == name:
            return copy.deepcopy(display)
    raise KeyError(name)


def make_pointcloud(template, name, topic, color, alpha=0.32, size=0.07):
    display = copy.deepcopy(template)
    display.update(
        {
            "Class": "rviz/PointCloud2",
            "Name": name,
            "Enabled": True,
            "Value": True,
            "Topic": topic,
            "Alpha": alpha,
            "Color": color,
            "Color Transformer": "FlatColor",
            "Use rainbow": False,
            "Style": "Flat Squares",
            "Size (m)": size,
            "Size (Pixels)": 3,
            "Decay Time": 0,
            "Queue Size": 5,
        }
    )
    return display


def make_marker(template, name, topic):
    display = copy.deepcopy(template)
    display.update(
        {
            "Class": "rviz/Marker",
            "Name": name,
            "Enabled": True,
            "Value": True,
            "Marker Topic": topic,
            "Namespaces": {},
            "Queue Size": 20,
        }
    )
    return display


def make_group(name, displays):
    return {
        "Class": "rviz/Group",
        "Name": name,
        "Enabled": True,
        "Value": True,
        "Displays": displays,
    }


def set_camera(config):
    manager = config["Visualization Manager"]
    manager["Global Options"].update(
        {
            "Fixed Frame": "world",
            "Background Color": "255; 255; 255",
            "Frame Rate": 30,
        }
    )
    view = manager["Views"]["Current"]
    view.update(
        {
            "Class": "rviz/ThirdPersonFollower",
            "Distance": 60,
            "Focal Point": {"X": 0.0, "Y": 0.0, "Z": 0.0},
            "Pitch": 1.25,
            "Yaw": -1.5708,
            "Target Frame": "<Fixed Frame>",
        }
    )


def build_config(base, single):
    config = copy.deepcopy(base)
    manager = config["Visualization Manager"]
    source_displays = manager["Displays"]
    simulation_map = find_display(source_displays, "simulation_map")
    local_template = find_display(source_displays, "occupied_all")
    marker_template = find_display(source_displays, "position_cmd")
    grid = find_display(source_displays, "Grid")
    target = find_display(source_displays, "target_search")
    trail = find_display(source_displays, "trails")
    robot_template = find_display(source_displays, "robot_d1")
    executed_template = find_display(source_displays, "executed_traj")

    global_map = make_pointcloud(
        simulation_map,
        "global_obstacles",
        "/map_generator/global_cloud",
        "150; 155; 165",
        alpha=0.22,
        size=0.055,
    )
    global_map["Autocompute Value Bounds"] = {
        "Max Value": 2.5,
        "Min Value": -0.2,
        "Value": False,
    }
    grid.update({"Enabled": True, "Value": True, "Cell Size": 1, "Plane Cell Count": 40})

    if single:
        local_maps = [
            make_pointcloud(
                local_template,
                "drone1_local_map",
                "/sdf_map/occupancy_all",
                DRONE_COLORS[1],
                alpha=0.28,
                size=0.065,
            )
        ]
        fovs = [make_marker(marker_template, "drone1_fov", "/planning/position_cmd_vis")]
        trajectories = [
            make_marker(executed_template, "drone1_trajectory", "/planning/travel_traj")
        ]
        robots = [make_marker(robot_template, "drone1_robot", "/odom_visualization/robot")]
        target.update({"Enabled": False, "Value": False})
        trail.update({"Enabled": False, "Value": False})
    else:
        local_maps = [
            make_pointcloud(
                local_template,
                f"drone{i}_local_map",
                f"/drone{i}/sdf_map/occupancy_all",
                DRONE_COLORS[i],
                alpha=0.26,
                size=0.065,
            )
            for i in (1, 2, 3)
        ]
        fovs = [
            make_marker(marker_template, f"drone{i}_fov", f"/drone{i}/planning/position_cmd_vis")
            for i in (1, 2, 3)
        ]
        trajectories = []
        robots = []
        for drone_id in (1, 2, 3):
            robot = make_marker(
                robot_template,
                f"drone{drone_id}_robot",
                f"/drone{drone_id}/odom_visualization/robot",
            )
            robot["Namespaces"] = {"mesh": True}
            robots.append(robot)
        target.update({"Enabled": True, "Value": True})
        trail.update({"Enabled": True, "Value": True})

    manager["Displays"] = [
        grid,
        make_group("Scene Map", [global_map]),
        make_group("Local Maps", local_maps),
        make_group("Camera FOV", fovs),
        make_group("Trajectories", trajectories) if trajectories else {},
        make_group("Multi Trails", [trail]) if not single else {},
        make_group("Robots", robots),
        make_group("Target", [target]) if not single else {},
    ]
    manager["Displays"] = [item for item in manager["Displays"] if item]
    set_camera(config)
    return config


def main():
    with open(BASE_PATH, encoding="utf-8") as handle:
        base = yaml.safe_load(handle)
    os.makedirs(OUT_DIR, exist_ok=True)
    for filename, single in (
        ("record_single_full.rviz", True),
        ("record_multi_full.rviz", False),
    ):
        output = os.path.join(OUT_DIR, filename)
        with open(output, "w", encoding="utf-8") as handle:
            yaml.safe_dump(build_config(base, single), handle, sort_keys=False, allow_unicode=True)
        print("WROTE", output)


if __name__ == "__main__":
    main()
