# collisions.py
from panda3d.core import BitMask32

from panda3d.core import (
    CollisionNode, CollisionSphere, CollisionBox,
    CollisionTraverser, CollisionHandlerPusher,
    CollisionHandlerEvent
)

MASK_PLAYER = BitMask32.bit(0)
MASK_PLANET = BitMask32.bit(1)
MASK_DRONE  = BitMask32.bit(2)
MASK_STATIC = BitMask32.bit(3)

# ----------------------------------------------------
# Base collider metadata classes
# ----------------------------------------------------

class SphereCollideObj:
    """Attach this to any object that should use a sphere hitbox."""
    def __init__(self, radius, debug=True):
        self.collider_type = "sphere"
        self.collider_radius = radius
        self.debug_mode = debug
        self.collider = None


class BoxCollideObj:
    """Attach this to any object that should use a box hitbox."""
    def __init__(self, size_xyz, debug=True):
        self.collider_type = "box"
        self.collider_size = size_xyz  # (x, y, z)
        self.debug_mode = debug
        self.collider = None


class MultiBoxCollideObj:
    """Attach this to objects like the space station with multiple boxes."""
    def __init__(self, box_list, debug=True):
        self.collider_type = "multi_box"
        self.collider_boxes = box_list  # list of {center:(x,y,z), size:(x,y,z)}
        self.debug_mode = debug
        self.collider = None


# ----------------------------------------------------
# Collision Manager
# ----------------------------------------------------

class CollisionManager:
    def __init__(self, base):
        self.base = base

        # Main traverser
        self.traverser = CollisionTraverser("mainTraverser")
        # Optional: let Panda auto-run it as well
        self.base.cTrav = self.traverser

        # Handlers
        self.pusher = CollisionHandlerPusher()
        self.events = CollisionHandlerEvent()

        # Event pattern: "fromNode-into-intoNode"
        self.events.addInPattern("%fn-into-%in")

        print("\n[CollisionManager] Initialized.")
        print("[CollisionManager] Traverser name:", self.traverser.getName())

    # ----------------------------------------------------
    # Create collider for ANY object
    # ----------------------------------------------------
    def create_collider(self, obj):
        """
        Creates and attaches a CollisionNode to obj.node based on obj.collider_type.
        Stores the NodePath in obj.collider and returns it.
        """

        if not hasattr(obj, "collider_type"):
            print(f"[CollisionManager] WARNING: {obj} has no collider_type; skipping.")
            return None

        # MULTI-BOX (space station)
        if obj.collider_type == "multi_box":
            cnode = CollisionNode(obj.name)
            for box in obj.collider_boxes:
                cx, cy, cz = box["center"]
                sx, sy, sz = box["size"]
                solid = CollisionBox((cx, cy, cz), sx, sy, sz)
                cnode.addSolid(solid)

            cpath = obj.node.attachNewNode(cnode)
            if obj.debug_mode:
                cpath.show()
            else:
                cpath.hide()

            obj.collider = cpath
            print(f"[CollisionManager] Created MULTI-BOX collider for {obj.name} with {len(obj.collider_boxes)} boxes.")
            return cpath

        # SPHERE
        elif obj.collider_type == "sphere":
            cnode = CollisionNode(obj.name)
            solid = CollisionSphere(0, 0, 0, obj.collider_radius)
            cnode.addSolid(solid)

        # BOX
        elif obj.collider_type == "box":
            cnode = CollisionNode(obj.name)
            x, y, z = obj.collider_size
            solid = CollisionBox((0, 0, 0), x, y, z)
            cnode.addSolid(solid)

        # NONE / unsupported
        else:
            print(f"[CollisionManager] No collider created for {obj.name} (collider_type={obj.collider_type}).")
            return None

        # Attach collider to the object's root node (not scaled)
        cpath = obj.node.attachNewNode(cnode)
        if obj.debug_mode:
            cpath.show()
        else:
            cpath.hide()

        obj.collider = cpath
        print(f"[CollisionManager] Created {obj.collider_type.upper()} collider for {obj.name}.")
        return cpath

    # ----------------------------------------------------
    # Player uses PUSH collisions (solid)
    # ----------------------------------------------------
    def register_player(self, player):
        cpath = self.create_collider(player)
        if cpath:
            # Player is FROM
            cpath.node().setFromCollideMask(MASK_PLAYER)
            cpath.node().setIntoCollideMask(BitMask32.allOff())

            # Player collides INTO planets, drones, station
            player.node.setCollideMask(MASK_PLANET | MASK_DRONE | MASK_STATIC)

            self.pusher.addCollider(cpath, player.node)
            self.traverser.addCollider(cpath, self.pusher)

            print("[CollisionManager] Player collider registered:", player.name)


    # ----------------------------------------------------
    # Static objects (planets, station, etc.)
    # ----------------------------------------------------
    def register_static(self, obj):
        cpath = self.create_collider(obj)
        if cpath:
            cpath.node().setFromCollideMask(BitMask32.allOff())
            cpath.node().setIntoCollideMask(MASK_PLANET)

            print("[CollisionManager] Static collider registered:", obj.name)


    # ----------------------------------------------------
    # Drones use EVENT collisions
    # ----------------------------------------------------
    def register_drone(self, drone):
        cpath = self.create_collider(drone)
        if cpath:
            # Drone is FROM
            cpath.node().setFromCollideMask(MASK_DRONE)
            cpath.node().setIntoCollideMask(BitMask32.allOff())

            # Drone only collides INTO the player
            drone.node.setCollideMask(MASK_PLAYER)

            self.traverser.addCollider(cpath, self.events)

            print("[CollisionManager] Drone collider registered:", drone.name)


    # ----------------------------------------------------
    # Event callbacks
    # ----------------------------------------------------
    def setup_events(self):
        # Names must match the CollisionNode names (we use obj.name)
        self.base.accept("PlayerShip-into-Drone_*", self.on_player_hits_drone)
        self.base.accept("PlayerShip-into-PLANET*", self.on_player_hits_planet)
        self.base.accept("PlayerShip-into-MainStation", self.on_player_hits_station)

        print("[CollisionManager] Event hooks set up:")
        print("  - PlayerShip-into-Drone_*")
        print("  - PlayerShip-into-PLANET*")
        print("  - PlayerShip-into-MainStation")

    def on_player_hits_drone(self, entry):
        print("[CollisionManager] Player collided with drone:", entry.getIntoNode().getName())

    def on_player_hits_planet(self, entry):
        print("[CollisionManager] Player collided with planet:", entry.getIntoNode().getName())

    def on_player_hits_station(self, entry):
        print("[CollisionManager] Player collided with the space station!")

    # ----------------------------------------------------
    # Manual update (if you still want the task)
    # ----------------------------------------------------
    def update(self, task):
        self.traverser.traverse(self.base.render)
        return task.cont