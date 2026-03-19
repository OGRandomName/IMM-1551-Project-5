#spacejam.py
import math
import os
import random

from direct.showbase.ShowBase import ShowBase
from direct.showbase import ShowBaseGlobal
from panda3d.core import ClockObject

from collisions import CollisionManager

from classes import (
    Planet,
    SpaceStation,
    Player,
    DroneDefender,
    Universe,
    DroneCounter,
    
)
from dronepatterns import (
    circleX_pattern,
    circleY_pattern,
    circleZ_pattern,
    cloud_pattern,
    baseball_seams_pattern
)

# ---------------------------------------------------------
# GLOBAL PERFORMANCE MODE
# ---------------------------------------------------------
# True  = fewer drones, fewer decorated planets, more culling, lighter CPU load
# False = full visual experience
PERFORMANCE_MODE = True

PATTERN_FUNCTIONS = [
    circleX_pattern,
    circleY_pattern,
    circleZ_pattern,
    cloud_pattern,
    baseball_seams_pattern
]


class SpaceJam(ShowBase):
    def __init__(self):
        super().__init__()

        # Make sure ShowBaseGlobal.base is this instance
        ShowBaseGlobal.base = self

        self.accept("escape", self.userExit)

        self.drone_counter = DroneCounter()
        self.orbiting_drones = []
        self.planets = []

        self.setup_lights()
        self.setup_universe()
        self.setup_player()
        self.setup_camera()
        self.setup_space_station()
        self.setup_planets()

        # -----------------------------------------
        # COLLISION MANAGER (Panda3D collision engine)
        # -----------------------------------------
        self.collision_manager = CollisionManager(self)

        print("\n=== COLLISION MANAGER START ===")
        print("Planets in list:", len(self.planets))
        print("Drones in list:", len(self.orbiting_drones))

        # Player
        self.collision_manager.register_player(self.player)

        # Planets
        for planet in self.planets:
            self.collision_manager.register_static(planet)

        # Space Station
        self.collision_manager.register_static(self.station)

        # Drones
        for drone in self.orbiting_drones:
            self.collision_manager.register_drone(drone)

        self.collision_manager.setup_events()
        self.taskMgr.add(self.collision_manager.update, "collisionEngineUpdate")
        # Missile interval cleanup task
        self.taskMgr.add(self.player.CheckIntervals, "checkMissiles", priority=34)


        # -----------------------------------------
        # DRONE ORBIT UPDATE (single task for all drones)
        # -----------------------------------------
        self.taskMgr.add(self.update_drone_orbits, "updateDroneOrbits")

        # -----------------------------------------
        # MOVEMENT KEY BINDINGS
        # -----------------------------------------
        self.accept("w", self.player.Thrust, [1])
        self.accept("w-up", self.player.Thrust, [0])

        self.accept("s", self.player.ReverseThrust, [1])
        self.accept("s-up", self.player.ReverseThrust, [0])

        self.accept("a", self.player.RollLeft, [1])
        self.accept("a-up", self.player.RollLeft, [0])

        self.accept("d", self.player.RollRight, [1])
        self.accept("d-up", self.player.RollRight, [0])

        self.accept("space", self.player.MoveUp, [1])
        self.accept("space-up", self.player.MoveUp, [0])

        self.accept("shift", self.player.MoveDown, [1])
        self.accept("shift-up", self.player.MoveDown, [0])

        self.accept("q", self.player.LeftTurn, [1])
        self.accept("q-up", self.player.LeftTurn, [0])

        self.accept("e", self.player.RightTurn, [1])
        self.accept("e-up", self.player.RightTurn, [0])

        self.accept("mouse1", self.player.Fire)   # left click fires missile


    # -------------------------
    # Drone orbit update (single task)
    # -------------------------
    def update_drone_orbits(self, task):
        dt = ClockObject.getGlobalClock().getDt()

        # In performance mode, skip some frames to reduce CPU load
        if PERFORMANCE_MODE and random.random() < 0.5:
            return task.cont

        for drone in self.orbiting_drones:
            drone.orbit_angle += drone.orbit_speed * dt

            cx, cy, cz = drone.orbit_center

            x = cx + drone.orbit_radius * math.cos(drone.orbit_angle)
            y = cy + drone.orbit_radius * math.sin(drone.orbit_angle)
            z = cz  # flat orbit; patterns can change this if needed

            drone.node.setPos(x, y, z)

        return task.cont

    # -------------------------
    # Lighting
    # -------------------------
    def setup_lights(self):
        from panda3d.core import AmbientLight, DirectionalLight, Vec4

        ambient = AmbientLight("ambient")
        ambient.setColor(Vec4(0.2, 0.2, 0.25, 1))
        ambient_np = self.render.attachNewNode(ambient)
        self.render.setLight(ambient_np)

        dlight = DirectionalLight("dlight")
        dlight.setColor(Vec4(0.8, 0.8, 0.7, 1))
        dlight_np = self.render.attachNewNode(dlight)
        dlight_np.setHpr(45, -60, 0)
        self.render.setLight(dlight_np)

    # -------------------------
    # Universe (Skybox)
    # -------------------------
    def setup_universe(self):
        self.universe = Universe(
            model_path="Assets/Universe/Universe.egg",
            scale=15000,
            position=(0, 0, 0)
        )

    # -------------------------
    # Player (Spaceship)
    # -------------------------
    def setup_player(self):
        self.player = Player(
            name="PlayerShip",
            model_path="Assets/spaceships/Dumbledore.egg",
            scale=1.5,
            position=(0, -30, 0)
        )

    # -------------------------
    # Camera
    # -------------------------
    def setup_camera(self):
        self.disableMouse()
        self.camera.reparentTo(self.player.model)
        self.camera.setFluidPos(0, -40, 10)
        self.camera.setHpr(0, -10, 0)

    # -------------------------
    # Drone Ring Creator (optional helper)
    # -------------------------
    def create_drone_ring(self, center_pos, num_drones=6, radius=10):
        drones = []
        cx, cy, cz = center_pos

        for i in range(num_drones):
            angle = (2 * math.pi / num_drones) * i
            x = cx + radius * math.cos(angle)
            z = cz + radius * math.sin(angle)
            y = cy

            drone = DroneDefender(
                name=f"Drone_{i}",
                model_path="Assets/DroneDefender/DroneDefender.egg",
                scale=0.5,
                position=(x, y, z),
                orbit_radius=radius
            )

            # Basic orbit metadata
            drone.orbit_center = center_pos
            drone.orbit_angle = angle
            drone.orbit_speed = 0.3

            drones.append(drone)
            self.orbiting_drones.append(drone)
            self.drone_counter.register_drone()

        return drones

    # -------------------------
    # Space Station
    # -------------------------
    def setup_space_station(self):

        # Accurate multi‑box collider scaled ×3
        station_boxes = [
            {"center": (3, -2, -4), "size": (16, 15, 30)},     # central tower

            {"center": (0, 0, -5), "size": (28, 28, .5)},   # ring middle
            {"center": (-30, 30, -15), "size": (12, 12, 6)},   # ring left

        ]

        # Create the station with collider
        self.station = SpaceStation(
            name="MainStation",
            model_path="Assets/space station/spaceStation.egg",
            scale=3.0,
            position=(20, 10, 0),
            box_list=station_boxes
        )
        self.station.node.setHpr(0, 0, 0)

    # -------------------------
    # Planets + Drone Patterns
    # -------------------------
    def setup_planets(self):
        print("\n=== SETUP PLANETS STARTED ===")

        planet_textures = [
            "planet-texture.png",
            "planet-texture1.png",
            "planet-texture2.png",
            "planet-texture3.png",
            "planet-texture4.png",
            "planet-texture5.png",
            "planet-texture6.png",
            "planet-texture7.png",
            "planet-texture8.png",
        ]

        placed_planets = []

        # Spacing and distance tuned by performance mode
        if PERFORMANCE_MODE:
            min_distance_factor = 8
            distance_min, distance_max = 3000, 12000
            y_min, y_max = -3000, 6000
        else:
            min_distance_factor = 10
            distance_min, distance_max = 2000, 10000
            y_min, y_max = -2000, 5000

        planet_positions = []

        for i, tex_name in enumerate(planet_textures):
            print(f"\n--- Generating planet {i+1} ---")

            for attempt in range(200):
                distance = random.uniform(distance_min, distance_max)
                angle = random.uniform(0, 2 * math.pi)
                y = random.uniform(y_min, y_max)
                z = random.uniform(-1000, 1000)
                x = distance * math.cos(angle)

                scale = random.uniform(200, 400)
                radius = scale / 2

                overlap = False
                for px, py, pz, pradius in placed_planets:
                    d = math.sqrt((x - px) ** 2 + (y - py) ** 2 + (z - pz) ** 2)
                    if d < min_distance_factor * (radius + pradius):
                        overlap = True
                        break

                if not overlap:
                    break

            print(f"Planet {i+1} position: ({x:.1f}, {y:.1f}, {z:.1f}) scale={scale:.1f}")

            # Hide distance tuned by performance mode
            hide_distance = 10000 if PERFORMANCE_MODE else 12000

            planet = Planet(
                name=f"PLANET{i+1}",
                model_path="Assets/planets/protoPlanet.obj",
                scale=scale,
                position=(x, y, z),
                texture_path=os.path.join("Assets/planets", tex_name),
                enable_collisions=True,
                hide_distance=hide_distance
            )

            print("Loaded planet model:", planet.model)

            placed_planets.append((x, y, z, radius))
            planet_positions.append((x, y, z, scale))
            self.planets.append(planet)

            print(f"Planet {i+1} appended. Total so far: {len(self.planets)}")

        print("\n=== PLANET GENERATION COMPLETE ===")
        print("Total planets created:", len(self.planets))

        # Apply unique random patterns to planets
        if PERFORMANCE_MODE:
            num_planets_to_decorate = 2
        else:
            num_planets_to_decorate = min(len(PATTERN_FUNCTIONS), random.randint(3, 6))

        chosen_planets = random.sample(planet_positions, num_planets_to_decorate)
        unique_patterns = random.sample(PATTERN_FUNCTIONS, num_planets_to_decorate)

        print(f"\nDecorating {num_planets_to_decorate} planets with patterns...")

        for (planet_data, pattern_func) in zip(chosen_planets, unique_patterns):
            px, py, pz, scale = planet_data
            print(f"Applying pattern {pattern_func.__name__} to planet at ({px:.1f}, {py:.1f}, {pz:.1f})")

            # Drone count tuned by performance mode
            drone_count = 8 if PERFORMANCE_MODE else 20

            drones = pattern_func(
                self,
                center_pos=(px, py, pz),
                num_drones=drone_count,
                radius=scale * 2
            )

            for drone in drones:
                drone.model.setScale(10.0)
                self.orbiting_drones.append(drone)
                self.drone_counter.register_drone()

        print("\n=== SETUP PLANETS FINISHED ===")
        print("Total drones spawned:", self.drone_counter.get_count())
        print(f"Decorated {num_planets_to_decorate} planets with random patterns.")


app = SpaceJam()
app.run()
