import math
import random
from classes import DroneDefender

# ---------------------------------------------------------
# Helper: generate evenly spaced angles
# ---------------------------------------------------------
def evenly_spaced_angles(n):
    step = (2 * math.pi) / n
    return [i * step for i in range(n)]

# ---------------------------------------------------------
# Circle X Pattern (YZ plane)
# ---------------------------------------------------------
def circleX_pattern(game, center_pos, num_drones=12, radius=20):
    drones = []
    cx, cy, cz = center_pos
    angles = evenly_spaced_angles(num_drones)

    for i, angle in enumerate(angles):
        x = cx
        y = cy + radius * math.cos(angle)
        z = cz + radius * math.sin(angle)

        drone = DroneDefender(
            name=f"DroneX_{i}",
            model_path="Assets/DroneDefender/DroneDefender.egg",
            scale=0.5,
            position=(x, y, z),
            orbit_radius=radius
        )

        drone.orbit_center = center_pos
        drone.orbit_angle = angle
        drone.orbit_speed = 0.3

        drones.append(drone)

    return drones

# ---------------------------------------------------------
# Circle Y Pattern (XZ plane)
# ---------------------------------------------------------
def circleY_pattern(game, center_pos, num_drones=12, radius=20):
    drones = []
    cx, cy, cz = center_pos
    angles = evenly_spaced_angles(num_drones)

    for i, angle in enumerate(angles):
        x = cx + radius * math.cos(angle)
        y = cy
        z = cz + radius * math.sin(angle)

        drone = DroneDefender(
            name=f"DroneY_{i}",
            model_path="Assets/DroneDefender/DroneDefender.egg",
            scale=0.5,
            position=(x, y, z),
            orbit_radius=radius
        )

        drone.orbit_center = center_pos
        drone.orbit_angle = angle
        drone.orbit_speed = 0.3

        drones.append(drone)

    return drones

# ---------------------------------------------------------
# Circle Z Pattern (XY plane)
# ---------------------------------------------------------
def circleZ_pattern(game, center_pos, num_drones=12, radius=20):
    drones = []
    cx, cy, cz = center_pos
    angles = evenly_spaced_angles(num_drones)

    for i, angle in enumerate(angles):
        x = cx + radius * math.cos(angle)
        y = cy + radius * math.sin(angle)
        z = cz

        drone = DroneDefender(
            name=f"DroneZ_{i}",
            model_path="Assets/DroneDefender/DroneDefender.egg",
            scale=0.5,
            position=(x, y, z),
            orbit_radius=radius
        )

        drone.orbit_center = center_pos
        drone.orbit_angle = angle
        drone.orbit_speed = 0.3

        drones.append(drone)

    return drones

# ---------------------------------------------------------
# Cloud Pattern (random points on a sphere)
# ---------------------------------------------------------
def cloud_pattern(game, center_pos, num_drones=20, radius=40):
    drones = []
    cx, cy, cz = center_pos

    for i in range(num_drones):
        # Random point on sphere using fast method
        theta = random.random() * 2 * math.pi
        phi = math.acos(2 * random.random() - 1)

        x = cx + radius * math.sin(phi) * math.cos(theta)
        y = cy + radius * math.sin(phi) * math.sin(theta)
        z = cz + radius * math.cos(phi)

        drone = DroneDefender(
            name=f"CloudDrone_{i}",
            model_path="Assets/DroneDefender/DroneDefender.egg",
            scale=0.5,
            position=(x, y, z),
            orbit_radius=radius
        )

        drone.orbit_center = center_pos
        drone.orbit_angle = theta
        drone.orbit_speed = 0.2

        drones.append(drone)

    return drones

# ---------------------------------------------------------
# Baseball Seams Pattern (optimized)
# ---------------------------------------------------------
def baseball_seams_pattern(game, center_pos, num_drones=20, radius=40):
    drones = []
    cx, cy, cz = center_pos
    angles = evenly_spaced_angles(num_drones)

    for i, t in enumerate(angles):
        # Seam 1
        x1 = cx + radius * math.cos(t)
        y1 = cy + radius * math.sin(t)
        z1 = cz + radius * 0.3 * math.sin(2 * t)

        drone1 = DroneDefender(
            name=f"Seam1_{i}",
            model_path="Assets/DroneDefender/DroneDefender.egg",
            scale=0.5,
            position=(x1, y1, z1),
            orbit_radius=radius
        )

        drone1.orbit_center = center_pos
        drone1.orbit_angle = t
        drone1.orbit_speed = 0.25
        drones.append(drone1)

        # Seam 2 (opposite phase)
        t2 = t + math.pi
        x2 = cx + radius * math.cos(t2)
        y2 = cy + radius * math.sin(t2)
        z2 = cz + radius * 0.3 * math.sin(2 * t2)

        drone2 = DroneDefender(
            name=f"Seam2_{i}",
            model_path="Assets/DroneDefender/DroneDefender.egg",
            scale=0.5,
            position=(x2, y2, z2),
            orbit_radius=radius
        )

        drone2.orbit_center = center_pos
        drone2.orbit_angle = t2
        drone2.orbit_speed = 0.25
        drones.append(drone2)

    return drones
