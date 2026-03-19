#classes.py
from direct.showbase import ShowBaseGlobal
from panda3d.core import (
    Texture, ClockObject, Vec3, TextureStage, LODNode,
    CollisionNode, CollisionSphere, TransparencyAttrib
)

# Collider metadata
from collisions import SphereCollideObj, BoxCollideObj, MultiBoxCollideObj

from direct.gui.OnscreenImage import OnscreenImage


DEBUG_COLLIDERS = True


# ============================================================
# Base Class: SpaceObject (visual only)
# ============================================================
class SpaceObject:
    def __init__(self, name, model_path, scale, position,
                 collider_type="sphere", health=100, texture_path=None):

        self.name = name
        self.model_path = model_path
        self.scale = scale
        self.position = position
        self.collider_type = collider_type
        self.health = health
        self.texture_path = texture_path

        # ROOT NODE (no scale!)
        self.node = ShowBaseGlobal.base.render.attachNewNode(self.name + "_ROOT")
        self.node.setPos(*self.position)

        # Load model under the root
        self.model = ShowBaseGlobal.base.loader.loadModel(self.model_path)
        self.model.reparentTo(self.node)

        # Apply scale to MODEL, not root
        self.model.setScale(self.scale)

        # Tag
        self.model.setTag("objectType", self.name)

        # Texture override
        if self.texture_path:
            tex = ShowBaseGlobal.base.loader.loadTexture(self.texture_path)
            if tex:
                self.model.setTexture(tex, 1)

    def set_position(self, pos):
        self.position = pos
        self.node.setPos(*pos)


# ============================================================
# Universe (no collisions)
# ============================================================
class Universe:
    def __init__(self, model_path, scale=15000, position=(0, 0, 0), texture_path=None):
        self.name = "Universe"
        self.model_path = model_path
        self.scale = scale
        self.position = position
        self.texture_path = texture_path

        self.collider_type = None
        self.debug_mode = False

        self.model = ShowBaseGlobal.base.loader.loadModel(self.model_path)
        self.model.reparentTo(ShowBaseGlobal.base.camera)
        self.model.setCompass()

        self.model.setPos(*self.position)
        self.model.setScale(self.scale)

        self.model.setTag("objectType", "Universe")

        if self.texture_path:
            tex = ShowBaseGlobal.base.loader.loadTexture(self.texture_path)
            if tex:
                self.model.setTexture(tex, 1)

        self.model.setTwoSided(True)


# ============================================================
# Planet (Sphere collider)
# ============================================================
import math

class Planet(SpaceObject, SphereCollideObj):
    def __init__(
        self,
        name,
        model_path,
        scale,
        position,
        texture_path=None,
        enable_collisions=True,
        hide_distance=5000,
        health=100
    ):
        SpaceObject.__init__(
            self,
            name=name,
            model_path=model_path,
            scale=scale,
            position=position,
            collider_type="sphere",
            health=health
        )

        self.hide_distance = hide_distance
        self.enable_collisions = enable_collisions

        if enable_collisions:
            SphereCollideObj.__init__(self, radius=scale / 2.0)
            self.debug_mode = DEBUG_COLLIDERS
        else:
            self.collider_type = "none"
            self.debug_mode = False

        if texture_path:
            tex = ShowBaseGlobal.base.loader.loadTexture(texture_path)
            self.model.setTexture(tex, 1)

        self.model.flattenStrong()
        self.model.setTwoSided(False)

        ShowBaseGlobal.base.taskMgr.add(self._distance_cull, f"planetCull_{name}")

    def _distance_cull(self, task):
        cam = ShowBaseGlobal.base.camera
        planet_pos = self.node.getPos(ShowBaseGlobal.base.render)
        cam_pos = cam.getPos(ShowBaseGlobal.base.render)

        dx = planet_pos.x - cam_pos.x
        dy = planet_pos.y - cam_pos.y
        dz = planet_pos.z - cam_pos.z
        dist_sq = dx*dx + dy*dy + dz*dz

        if dist_sq > (self.hide_distance * self.hide_distance):
            self.node.hide()
        else:
            self.node.show()

        return task.cont


# ============================================================
# Space Station (Multi‑box collider)
# ============================================================
class SpaceStation(SpaceObject, MultiBoxCollideObj):
    def __init__(self, name, model_path, scale, position, box_list, health=100):
        SpaceObject.__init__(
            self,
            name=name,
            model_path=model_path,
            scale=scale,
            position=position,
            collider_type="multi_box",
            health=health
        )

        MultiBoxCollideObj.__init__(self, box_list)
        self.debug_mode = DEBUG_COLLIDERS


# ============================================================
# Missile Class (must appear BEFORE Player)
# ============================================================
class Missile(SphereCollideObj):
    missileCount = 0
    Models = {}
    Colliders = {}
    Intervals = {}

    def __init__(self, name, model_path, scale, position):
        Missile.missileCount += 1

        self.name = name
        self.model_path = model_path
        self.scale = scale
        self.position = position

        self.node = ShowBaseGlobal.base.render.attachNewNode(name + "_ROOT")
        self.node.setPos(*position)

        self.model = ShowBaseGlobal.base.loader.loadModel(model_path)
        self.model.reparentTo(self.node)
        self.model.setScale(scale)

        SphereCollideObj.__init__(self, radius=1.0)
        self.debug_mode = DEBUG_COLLIDERS

        cnode = CollisionNode(name)
        cnode.addSolid(CollisionSphere(0, 0, 0, 1.0))
        cpath = self.node.attachNewNode(cnode)
        if DEBUG_COLLIDERS:
            cpath.show()
        self.collider = cpath

        Missile.Models[name] = self.model
        Missile.Colliders[name] = self.collider

        print(f"[Missile] Created missile {name}")


# ============================================================
# Player (Sphere collider + movement + missiles)
# ============================================================
class Player(SpaceObject, SphereCollideObj):
    def __init__(self, name, model_path, scale, position, health=100):
        SpaceObject.__init__(self, name, model_path, scale, position, health)

        SphereCollideObj.__init__(self, radius=3.0)
        self.debug_mode = DEBUG_COLLIDERS

        self.speed = 120
        self.turn_rate = 60

        self.model.reparentTo(self.node)

        # Missile system
        self.missileBay = 1
        self.maxMissiles = 1
        self.missileDistance = 200
        self.reloading = False
        self.reloadTime = 2.0

        # HUD
        self.crosshair = OnscreenImage(
            image="Assets/crosshair.png",
            pos=(0, 0, 0),
            scale=0.05
        )
        self.crosshair.setTransparency(TransparencyAttrib.MAlpha)

        ShowBaseGlobal.base.taskMgr.add(self.StabilizeRoll, "stabilize-roll")

    # -------------------------------------------------------
    # Missile Firing
    # -------------------------------------------------------
    def Fire(self):
        if self.missileBay > 0:
            forward = self.node.getQuat(ShowBaseGlobal.base.render).getForward()
            forward.normalize()

            startPos = self.node.getPos(ShowBaseGlobal.base.render) + forward * 4
            endPos = startPos + forward * self.missileDistance

            missileName = f"Missile_{Missile.missileCount + 1}"

            missile = Missile(
                name=missileName,
                model_path="Assets/spaceships/Dumbledore.egg",
                scale=0.5,
                position=startPos
            )

            interval = missile.node.posInterval(
                2.0,
                endPos,
                startPos=startPos,
                fluid=1
            )

            Missile.Intervals[missileName] = interval
            interval.start()

            self.missileBay -= 1
            print(f"[Player] Fired {missileName}")

        else:
            print("[Player] No missile in bay — reloading...")
            if not self.reloading:
                self.reloading = True
                ShowBaseGlobal.base.taskMgr.doMethodLater(
                    0, self.Reload, "reloadTask"
                )

    def Reload(self, task):
        if task.time >= self.reloadTime:
            self.missileBay = min(self.missileBay + 1, self.maxMissiles)
            print(f"[Player] Reload complete. Missiles in bay: {self.missileBay}")
            self.reloading = False
            return task.done
        return task.cont

    def CheckIntervals(self, task):
        finished = []

        for name, interval in list(Missile.Intervals.items()):
            if interval.isStopped():
                finished.append(name)

        for name in finished:
            print(f"[Player] Missile {name} finished — deleting")

            if name in Missile.Models:
                Missile.Models[name].removeNode()
                del Missile.Models[name]

            if name in Missile.Colliders:
                Missile.Colliders[name].removeNode()
                del Missile.Colliders[name]

            if name in Missile.Intervals:
                del Missile.Intervals[name]

        return task.cont

    # -------------------------------------------------------
    # MOVEMENT — always move the ROOT (self.node)
    # -------------------------------------------------------
    def Thrust(self, keyDown):
        if keyDown:
            ShowBaseGlobal.base.taskMgr.add(self.ApplyThrust, "forward-thrust")
        else:
            ShowBaseGlobal.base.taskMgr.remove("forward-thrust")

    def ApplyThrust(self, task):
        dt = ClockObject.getGlobalClock().getDt()
        cam_h = ShowBaseGlobal.base.camera.getH(ShowBaseGlobal.base.render)
        self.node.setH(cam_h)
        self.node.setY(self.node, self.speed * dt)
        return task.cont

    def ReverseThrust(self, keyDown):
        if keyDown:
            ShowBaseGlobal.base.taskMgr.add(self.ApplyReverseThrust, "reverse-thrust")
        else:
            ShowBaseGlobal.base.taskMgr.remove("reverse-thrust")

    def ApplyReverseThrust(self, task):
        dt = ClockObject.getGlobalClock().getDt()
        cam_h = ShowBaseGlobal.base.camera.getH(ShowBaseGlobal.base.render)
        self.node.setH(cam_h)
        self.node.setY(self.node, -self.speed * dt)
        return task.cont

    def MoveUp(self, keyDown):
        if keyDown:
            ShowBaseGlobal.base.taskMgr.add(self.ApplyMoveUp, "move-up")
        else:
            ShowBaseGlobal.base.taskMgr.remove("move-up")

    def ApplyMoveUp(self, task):
        dt = ClockObject.getGlobalClock().getDt()
        self.node.setZ(self.node.getZ() + self.speed * dt)
        return task.cont

    def MoveDown(self, keyDown):
        if keyDown:
            ShowBaseGlobal.base.taskMgr.add(self.ApplyMoveDown, "move-down")
        else:
            ShowBaseGlobal.base.taskMgr.remove("move-down")

    def ApplyMoveDown(self, task):
        dt = ClockObject.getGlobalClock().getDt()
        self.node.setZ(self.node.getZ() - self.speed * dt)
        return task.cont

    def LeftTurn(self, keyDown):
        if keyDown:
            ShowBaseGlobal.base.taskMgr.add(self.ApplyLeftTurn, "left-turn")
        else:
            ShowBaseGlobal.base.taskMgr.remove("left-turn")

    def ApplyLeftTurn(self, task):
        dt = ClockObject.getGlobalClock().getDt()
        self.node.setH(self.node.getH() + self.turn_rate * dt)
        return task.cont

    def RightTurn(self, keyDown):
        if keyDown:
            ShowBaseGlobal.base.taskMgr.add(self.ApplyRightTurn, "right-turn")
        else:
            ShowBaseGlobal.base.taskMgr.remove("right-turn")

    def ApplyRightTurn(self, task):
        dt = ClockObject.getGlobalClock().getDt()
        self.node.setH(self.node.getH() - self.turn_rate * dt)
        return task.cont

    def RollLeft(self, keyDown):
        if keyDown:
            ShowBaseGlobal.base.taskMgr.add(self.ApplyRollLeft, "roll-left")
        else:
            ShowBaseGlobal.base.taskMgr.remove("roll-left")

    def ApplyRollLeft(self, task):
        dt = ClockObject.getGlobalClock().getDt()
        self.node.setR(self.node.getR() + self.turn_rate * dt)
        return task.cont

    def RollRight(self, keyDown):
        if keyDown:
            ShowBaseGlobal.base.taskMgr.add(self.ApplyRollRight, "roll-right")
        else:
            ShowBaseGlobal.base.taskMgr.remove("roll-right")

    def ApplyRollRight(self, task):
        dt = ClockObject.getGlobalClock().getDt()
        self.node.setR(self.node.getR() - self.turn_rate * dt)
        return task.cont

    def StabilizeRoll(self, task):
        dt = ClockObject.getGlobalClock().getDt()
        current_r = self.node.getR()
        target_r = 0
        damping = 4
        new_r = current_r + (target_r - current_r) * damping * dt
        self.node.setR(new_r)
        return task.cont


# ============================================================
# Drone (Sphere collider, drift‑free, smooth orbit)
# ============================================================
class DroneDefender(SpaceObject, SphereCollideObj):
    def __init__(self, name, model_path, scale, position, orbit_radius=20, health=10):
        SpaceObject.__init__(self, name, model_path, scale, position, health)

        SphereCollideObj.__init__(self, radius=2.0)
        self.debug_mode = DEBUG_COLLIDERS

        self.orbit_center = position
        self.orbit_radius = orbit_radius
        self.orbit_angle = 0.0
        self.orbit_speed = 0.5

        self.model.reparentTo(self.node)

    def update_orbit(self, task):
        dt = ClockObject.getGlobalClock().getDt()

        self.orbit_angle += self.orbit_speed * dt

        cx, cy, cz = self.orbit_center

        x = cx + self.orbit_radius * math.cos(self.orbit_angle)
        y = cy + self.orbit_radius * math.sin(self.orbit_angle)
        z = cz

        self.node.setPos(x, y, z)

        return task.cont


# ============================================================
# Drone Counter
# ============================================================
class DroneCounter:
    def __init__(self):
        self.count = 0

    def register_drone(self):
        self.count += 1

    def get_count(self):
        return self.count