import math
import copy
import random
import pygame

pygame.init()


class Vector(object):
    def __init__(self, *args):
        """ Create a vector, example: v = Vector(1,2) """
        if len(args) == 0:
            self.values = [0, 0]
        else:
            self.values = list(args)

    def norm(self):
        """ Returns the norm (length, magnitude) of the vector """
        return math.sqrt(sum(comp**2 for comp in self))

    def argument(self):
        """ Returns the argument of the vector, the angle clockwise from +x."""
        arg_in_rad = math.acos(Vector(1, 0).dot(self) / self.norm())
        if self.values[1] < 0:
            return 2 * math.pi - arg_in_rad
        else:
            return arg_in_rad

    def angle_to(self, other):
        return (self.argument() - other.argument()) % (2 * math.pi)

    def normalize(self):
        """ Returns a normalized unit vector """
        norm = self.norm()
        normed = list(comp / norm for comp in self)
        return Vector(*normed)

    def rotate(self, *args):
        """ Rotate this vector. If passed a number, assumes this is a
            2D vector and rotates by the passed value in degrees.  Otherwise,
            assumes the passed value is a list acting as a matrix which rotates the vector.
        """
        if len(args) == 1 and isinstance(args[0], (int, float)):
            # So, if rotate is passed an int or a float...
            if len(self) != 2:
                raise ValueError("Rotation axis not defined for greater than 2D vector")
            return self._rotate2D(*args)
        elif len(args) == 1:
            matrix = args[0]
            if not all(len(row) == len(v) for row in matrix) or not len(matrix) == len(self):
                raise ValueError("Rotation matrix must be square and same dimensions as vector")
            return self.matrix_mult(matrix)

    def _rotate2D(self, theta):
        """ Rotate this vector by theta in radians.

            Returns a new vector.
        """
        # Just applying the 2D rotation matrix
        dc, ds = math.cos(theta), math.sin(theta)
        x, y = self.values
        x, y = dc * x - ds * y, ds * x + dc * y
        return Vector(x, y)

    def matrix_mult(self, matrix):
        """ Multiply this vector by a matrix.  Assuming matrix is a list of lists.

            Example:
            mat = [[1,2,3],[-1,0,1],[3,4,5]]
            Vector(1,2,3).matrix_mult(mat) ->  (14, 2, 26)

        """
        if not all(len(row) == len(self) for row in matrix):
            raise ValueError('Matrix must match vector dimensions')

        # Grab a row from the matrix, make it a Vector, take the dot product,
        # and store it as the first component
        product = list(Vector(*row) * self for row in matrix)

        return Vector(*product)

    def dot(self, other):
        """ Returns the dot product of self and other vector
        """
        return sum(a * b for a, b in zip(self, other))

    def __mul__(self, other):
        """ Returns the dot product of self and other if multiplied
            by another Vector.  If multiplied by an int or float,
            multiplies each component by other.
        """
        if type(other) == type(self):
            product = list(a * b for a, b in zip(self, other))
        elif isinstance(other, (int, float)):
            product = list(a * other for a in self)
        return Vector(*product)

    def __rmul__(self, other):
        """ Called if 4*self for instance """
        return self.__mul__(other)

    def __truediv__(self, other):
        if type(other) == type(self):
            divided = list(a / b for a, b in zip(self, other))
        elif isinstance(other, (int, float)):
            divided = list(a / other for a in self)
        return Vector(*divided)

    def __add__(self, other):
        """ Returns the vector addition of self and other """
        if type(other) == type(self):
            added = list(a + b for a, b in zip(self, other))
        elif isinstance(other, (int, float)):
            added = list(a + other for a in self)
        return Vector(*added)

    def __sub__(self, other):
        """ Returns the vector difference of self and other """
        if type(other) == type(self):
            subbed = list(a - b for a, b in zip(self, other))
        elif isinstance(other, (int, float)):
            subbed = list(a - other for a in self)
        return Vector(*subbed)

    def __round__(self):
        """ Returns the vector rounded to 0 dp """
        rounded = list(round(a) for a in self)
        return Vector(*rounded)

    def __iter__(self):
        return self.values.__iter__()

    def __len__(self):
        return len(self.values)

    def __getitem__(self, key):
        return self.values[key]

    def __repr__(self):
        return str(self.values)


class Bat(object):
    def __init__(self, pos, angle):
        self.pos = pos
        self.vel = Vector()
        self.facing = Vector(1, 0).rotate(angle)
        self.ang_vel = 0
        self.friction = 1.1

        self.rays = list()
        self.beams = list()

        self.radius = BAT_RADIUS

    def update(self):
        self.pos += self.vel / 60
        self.test_collision()

        self.facing = self.facing.rotate(self.ang_vel / 60)

        self.vel /= self.friction
        self.ang_vel /= self.friction

    def test_collision(self):
        collide_index = self.get_rect().collidelist(walls)
        if collide_index != -1:
            if walls[collide_index].collides_bat:
                self.pos -= self.vel / 60
                rect = walls[collide_index].rect
                lengths = [abs(self.pos[0] - rect.left),
                           abs(self.pos[0] - rect.right),
                           abs(self.pos[1] - rect.top),
                           abs(self.pos[1] - rect.bottom)]
                close_edge = lengths.index(min(lengths))
                vel_index = close_edge not in (0, 1)
                positivity = (-1, 1)[close_edge % 2]

                self.vel.values[vel_index] = positivity * abs(self.vel[vel_index])

    def emit(self):
        for i in range(RAYS_PER_EMIT):
            angle = self.facing.argument() - EMISSION_ANGLE / 2 + EMISSION_ANGLE / RAYS_PER_EMIT * i
            self.rays.append(Ray(self, self.pos, angle))

    def test_rays(self, rays):
        removed_rays = list()
        for ray in rays:
            collision = self.get_rect().colliderect(ray.get_rect())
            if collision:
                if ray.collided and ray.exited_bat:
                    direction = -1 * ray.facing
                    if direction[0] or direction[1]:
                        direction = direction.normalize()
                        self.beams.append(Beam(self, self.pos, direction, ray.strength, ray.interest))
                    removed_rays.append(ray)

            elif not ray.exited_bat:
                ray.exited_bat = True

        for removed_ray in removed_rays:
            rays.remove(removed_ray)

    def get_average_beam(self):
        average_beam = Vector()
        for beam in self.beams:
            rel = beam.strength / RAY_STRENGTH * beam.rel * beam.interest
            average_beam += rel
        pygame.draw.line(screen, (255, 255, 255), round(self.pos), round(self.pos + BEAM_LENGTH * average_beam), 2 * BEAM_WIDTH)
        return average_beam

    def get_rect(self):
        return pygame.Rect(*round(self.pos - self.radius), 2 * self.radius, 2 * self.radius)

    def draw(self):
        pygame.draw.circle(screen, (255, 255, 255), round(self.pos), self.radius)
        pygame.draw.circle(screen, (164, 164, 255), round(self.pos + self.radius * self.facing), round(self.radius / 2))


class Ray:
    def __init__(self, parent, pos, angle):
        self.parent = parent

        self.pos = pos
        self.facing = Vector(1, 0).rotate(angle)

        self.collided = False
        self.exited_bat = False

        self.strength = RAY_STRENGTH
        self.interest = 0

        self.radius = RAY_RADIUS

    def update(self):
        self.strength -= RAY_DECAY
        self.test_collision()
        if self.strength <= 0:
            self.parent.rays.remove(self)
            return
        self.pos += self.facing * RAY_SPEED

    def test_collision(self):
        collide_index = self.get_rect().collidelist(walls)
        if collide_index != -1:
            if not self.collided:
                self.collided = True
            self.strength -= WALL_DECAY
            self.interest += walls[collide_index].interest
            self.interest /= 2
            self.pos -= (self.facing * RAY_SPEED) / 2
            rect = walls[collide_index].rect
            lengths = [abs(self.pos[0] - rect.left),
                       abs(self.pos[0] - rect.right),
                       abs(self.pos[1] - rect.top),
                       abs(self.pos[1] - rect.bottom)]
            close_edge = lengths.index(min(lengths))
            vel_index = close_edge not in (0, 1)
            positivity = (-1, 1)[close_edge % 2]

            self.facing.values[vel_index] = positivity * abs(self.facing[vel_index])

    def get_rect(self):
        return pygame.Rect(*round(self.pos - self.radius), 2 * self.radius, 2 * self.radius)

    def draw(self):
        positive_interest = round(255 * (abs(self.interest) + (self.interest)) / 2)
        negative_interest = round(255 * (abs(-self.interest) + (-self.interest)) / 2)
        pygame.draw.circle(screen, (negative_interest, positive_interest, 128), round(self.pos), self.radius)


class Beam:
    def __init__(self, parent, start, rel, strength, interest):
        self.parent = parent

        self.start = start
        self.rel = rel

        self.strength = strength
        self.interest = interest

        self.width = BEAM_WIDTH

    def update(self):
        self.strength -= BEAM_DECAY
        if self.strength <= 0:
            self.parent.beams.remove(self)
            return

    def draw(self):
        rel = BEAM_LENGTH * self.strength / RAY_STRENGTH * self.rel
        positive_interest = round(255 * (abs(self.interest) + (self.interest)) / 2)
        negative_interest = round(255 * (abs(-self.interest) + (-self.interest)) / 2)
        if DRAW_RELATIVE_BEAMS:
            pygame.draw.line(screen, (negative_interest, positive_interest, 128), round(self.parent.pos), round(self.parent.pos + rel), self.width)
        if DRAW_POSITION_BEAMS:
            pygame.draw.line(screen, (negative_interest, positive_interest, 128), round(self.start), round(self.start + rel), self.width)


class Wall(object):
    def __init__(self, topleft, size, interest, collides_bat):
        self.rect = pygame.Rect(*topleft, *size)
        self.interest = interest

        self.collides_bat = collides_bat

    def draw(self):
        positive_interest = round(255 * (abs(self.interest) + (self.interest)) / 2)
        negative_interest = round(255 * (abs(-self.interest) + (-self.interest)) / 2)
        pygame.draw.rect(screen, (negative_interest, positive_interest, 128), self.rect)


def main():
    global RAY_STRENGTH, RAY_DECAY, WALL_DECAY, BEAM_DECAY
    global RAY_SPEED, RAYS_PER_EMIT, EMISSION_ANGLE
    global BAT_RADIUS, RAY_RADIUS, BEAM_WIDTH, BEAM_LENGTH
    global DRAW_RELATIVE_BEAMS, DRAW_POSITION_BEAMS
    global screen, clock, bats, walls

    RAY_STRENGTH = 200
    RAY_DECAY = 1
    WALL_DECAY = 10
    BEAM_DECAY = 2

    RAY_SPEED = 8
    FRAMES_PER_EMIT = 16
    RAYS_PER_EMIT = 32
    EMISSION_ANGLE = 5 * math.pi / 4

    BAT_RADIUS = 10
    RAY_RADIUS = 4
    BEAM_WIDTH = 2
    BEAM_LENGTH = 100

    DRAW_WALLS = True
    DRAW_RAYS = True
    DRAW_RELATIVE_BEAMS = True
    DRAW_POSITION_BEAMS = True

    NUMBER_OF_BATS = 3
    AUTO_CONTROLLED = True
    DEFAULT_SPEED = 5
    DETECT_OTHER_RAYS = True

    screen = pygame.display.set_mode((1280, 720), pygame.RESIZABLE)
    clock = pygame.time.Clock()
    bats = list()
    for i in range(NUMBER_OF_BATS):
        bats.append(Bat(Vector(random.randint(0, screen.get_rect().width), random.randint(0, screen.get_rect().height)), 2 * math.pi * random.random()))
    walls = [Wall((0, 0), (screen.get_rect().w, 10), -0.5, True),
             Wall((0, 10), (10, screen.get_rect().h - 10), -0.5, True),
             Wall((screen.get_rect().w - 10, 10), (10, screen.get_rect().h - 10), -0.2, True),
             Wall((10, screen.get_rect().h - 10), (screen.get_rect().w - 20, 10), -0.1, True),
             Wall((150, 100), (50, 200), 0.2, False),
             Wall((1000, 200), (10, 300), -1, False),
             Wall((200, 500), (500, 10), -0.5, True),
             Wall((1100, 600), (50, 50), 1, False)]

    done = False
    frame = 0
    while not done:
        events = pygame.event.get()
        pressed = pygame.key.get_pressed()
        for event in events:
            if event.type == pygame.QUIT:
                quit()
            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    bats[0].emit()

        if not AUTO_CONTROLLED:
            if pressed[pygame.K_UP] or pressed[pygame.K_w]:
                bats[0].vel += 20 * bats[0].facing
            if pressed[pygame.K_DOWN] or pressed[pygame.K_s]:
                bats[0].vel -= 10 * bats[0].facing
            if pressed[pygame.K_LEFT] or pressed[pygame.K_a]:
                bats[0].ang_vel -= math.pi / 8
            if pressed[pygame.K_RIGHT] or pressed[pygame.K_d]:
                bats[0].ang_vel += math.pi / 8

        for bat in bats:
            if frame % FRAMES_PER_EMIT == 0:
                bat.emit()
            bat.update()
            for ray in bat.rays:
                ray.update()
            for beam in bat.beams:
                beam.update()

        screen.fill((0, 0, 0))
        if DRAW_WALLS:
            for wall in walls:
                wall.draw()
        for bat in bats:
            if DRAW_RAYS:
                for ray in bat.rays:
                    ray.draw()
            for beam in bat.beams:
                beam.draw()
            average_beam = bat.get_average_beam()

            if bat != bats[0] or AUTO_CONTROLLED:
                bat.vel += (20 * average_beam.norm() + DEFAULT_SPEED) * bat.facing
                if average_beam[0] or average_beam[1]:
                    angle = bat.facing.angle_to(average_beam)
                    if angle > math.pi:
                        angle -= math.pi * 2
                    bat.ang_vel -= angle
                else:
                    bat.ang_vel += math.pi
            bat.draw()
            if DETECT_OTHER_RAYS:
                for bat_emitter in bats:
                    bat.test_rays(bat_emitter.rays)
            else:
                bat.test_rays(bat.rays)
        pygame.display.flip()
        frame += 1
        clock.tick(60)


if __name__ == "__main__":
    main()