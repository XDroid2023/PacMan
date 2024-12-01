import pygame
import random
import math
from pygame import gfxdraw
import numpy

# Initialize Pygame
pygame.init()
pygame.font.init()
pygame.mixer.init(44100, -16, 2, 512)

# Constants
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
CELL_SIZE = 40
PLAYER_SPEED = 3.5
GHOST_SPEED = 2
WALL_COLOR = (24, 58, 145)  # Darker blue for walls
BACKGROUND_COLOR = (0, 0, 0)
PELLET_COLOR = (255, 255, 255)

# Colors
BLACK = (0, 0, 0)
YELLOW = (255, 255, 0)
RED = (255, 0, 0)
BLUE = (24, 58, 145)
WHITE = (255, 255, 255)
NEON_BLUE = (0, 255, 255)

# Set up the display
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Pacman")
clock = pygame.time.Clock()

# Load fonts
try:
    GAME_FONT = pygame.font.Font(None, 48)
    SCORE_FONT = pygame.font.Font(None, 36)
except:
    GAME_FONT = pygame.font.SysFont('arial', 48)
    SCORE_FONT = pygame.font.SysFont('arial', 36)

# Animation constants
PACMAN_ANIM_SPEED = 0.15
GHOST_ANIM_SPEED = 0.1
POWERUP_DURATION = 300

# Sound effects setup
def create_chomp_sound():
    duration = 100  # milliseconds
    frequency = 440  # Hz
    sample_rate = 44100
    n_samples = int(duration * sample_rate / 1000)
    
    # Generate a simple sine wave
    buf = numpy.zeros((n_samples, 2), dtype = numpy.int16)
    max_sample = 2**(16 - 1) - 1
    for s in range(n_samples):
        t = float(s) / sample_rate
        buf[s][0] = int(max_sample * math.sin(2 * math.pi * frequency * t))
        buf[s][1] = buf[s][0]  # Duplicate for stereo
    
    return pygame.sndarray.make_sound(buf)

def create_death_sound():
    duration = 500  # milliseconds
    frequency = 220  # Hz
    sample_rate = 44100
    n_samples = int(duration * sample_rate / 1000)
    
    buf = numpy.zeros((n_samples, 2), dtype = numpy.int16)
    max_sample = 2**(16 - 1) - 1
    for s in range(n_samples):
        t = float(s) / sample_rate
        # Decreasing frequency for death sound
        freq = frequency * (1.0 - t/(duration/1000))
        buf[s][0] = int(max_sample * math.sin(2 * math.pi * freq * t))
        buf[s][1] = buf[s][0]
    
    return pygame.sndarray.make_sound(buf)

# Create sound effects
try:
    chomp_sound = create_chomp_sound()
    death_sound = create_death_sound()
    SOUND_ENABLED = True
except ImportError:
    SOUND_ENABLED = False

class Wall:
    def __init__(self, x, y, width, height):
        self.rect = pygame.Rect(x, y, width, height)
        self.glow_value = random.random()
        self.glow_speed = random.uniform(0.02, 0.05)
        
    def draw(self):
        # Create a subtle pulsing effect for walls
        self.glow_value = (self.glow_value + self.glow_speed) % 1.0
        glow = math.sin(self.glow_value * math.pi * 2) * 0.2 + 0.8
        
        color = tuple(int(c * glow) for c in WALL_COLOR)
        
        # Draw main wall
        pygame.draw.rect(screen, color, self.rect)
        
        # Draw highlight edge
        highlight = (min(255, int(WALL_COLOR[0] * 1.5)), 
                    min(255, int(WALL_COLOR[1] * 1.5)), 
                    min(255, int(WALL_COLOR[2] * 1.5)))
        pygame.draw.line(screen, highlight, 
                        self.rect.topleft, self.rect.topright)
        pygame.draw.line(screen, highlight, 
                        self.rect.topleft, self.rect.bottomleft)

class Player:
    def __init__(self, walls):
        self.walls = walls
        self.radius = 15
        self.reset_position()
        self.direction = 0
        self.speed = PLAYER_SPEED
        self.score = 0
        self.current_direction = (0, 0)
        self.next_direction = (0, 0)
        self.mouth_angle = 0
        self.mouth_opening = True
        self.powerup_timer = 0
        self.chomp_timer = 0
        self.is_dead = False

    def reset_position(self):
        self.x = CELL_SIZE * 1.5
        self.y = CELL_SIZE * 1.5

    def can_move(self, x, y):
        temp_rect = pygame.Rect(x - self.radius, y - self.radius,
                              self.radius * 2, self.radius * 2)
        for wall in self.walls:
            if temp_rect.colliderect(wall.rect):
                return False
        return True

    def move(self):
        keys = pygame.key.get_pressed()
        
        # Update next_direction based on key press
        if keys[pygame.K_LEFT]:
            self.next_direction = (-1, 0)
            self.direction = 180
        elif keys[pygame.K_RIGHT]:
            self.next_direction = (1, 0)
            self.direction = 0
        elif keys[pygame.K_UP]:
            self.next_direction = (0, -1)
            self.direction = 90
        elif keys[pygame.K_DOWN]:
            self.next_direction = (0, 1)
            self.direction = 270

        # Try to move in next_direction if it's different from current
        if self.next_direction != self.current_direction:
            next_x = self.x + self.next_direction[0] * self.speed
            next_y = self.y + self.next_direction[1] * self.speed
            if self.can_move(next_x, next_y):
                self.current_direction = self.next_direction
            
        # Move in current direction if possible
        next_x = self.x + self.current_direction[0] * self.speed
        next_y = self.y + self.current_direction[1] * self.speed
        if self.can_move(next_x, next_y):
            self.x = next_x
            self.y = next_y
        else:
            # Try to slide along walls when hitting them at an angle
            next_x = self.x + self.current_direction[0] * self.speed
            if self.can_move(next_x, self.y):
                self.x = next_x
            
            next_y = self.y + self.current_direction[1] * self.speed
            if self.can_move(self.x, next_y):
                self.y = next_y

    def draw(self):
        # Animate mouth
        if self.current_direction != (0, 0):
            if self.mouth_opening:
                self.mouth_angle += PACMAN_ANIM_SPEED * 30
                if self.mouth_angle >= 45:
                    self.mouth_opening = False
            else:
                self.mouth_angle -= PACMAN_ANIM_SPEED * 30
                if self.mouth_angle <= 5:
                    self.mouth_opening = True
        
        # Draw Pacman body with gradient
        radius = self.radius
        x, y = int(self.x), int(self.y)
        
        # Draw main body with anti-aliasing
        pygame.gfxdraw.filled_circle(screen, x, y, radius, YELLOW)
        pygame.gfxdraw.aacircle(screen, x, y, radius, YELLOW)
        
        # Draw mouth
        if self.current_direction != (0, 0):
            start_angle = self.direction - self.mouth_angle
            end_angle = self.direction + self.mouth_angle
            points = [(x, y)]
            
            for angle in range(int(start_angle), int(end_angle), 5):
                rad = math.radians(angle)
                points.append((x + radius * math.cos(rad),
                             y - radius * math.sin(rad)))
            
            points.append((x, y))
            if len(points) > 2:
                pygame.gfxdraw.filled_polygon(screen, points, BLACK)
                pygame.gfxdraw.aapolygon(screen, points, BLACK)

    def collect_pellet(self):
        self.score += 10
        if self.chomp_timer <= 0:
            if SOUND_ENABLED:
                chomp_sound.play()
            self.chomp_timer = 10
        self.chomp_timer -= 1

    def die(self):
        if not self.is_dead:
            self.is_dead = True
            if SOUND_ENABLED:
                death_sound.play()
            pygame.time.wait(1)  # Small delay for death animation
    
class Ghost:
    def __init__(self, walls):
        self.walls = walls
        self.radius = 15
        self.respawn()
        self.path = []
        self.path_update_counter = 0
        self.path_update_frequency = 45
        self.chase_counter = 0
        self.chase_mode = True
        self.scatter_time = 180
        self.chase_time = 300
        self.wave_offset = random.random() * math.pi * 2
        self.color_shift = 0
        
    def respawn(self):
        corners = [
            (CELL_SIZE * 1.5, SCREEN_HEIGHT - CELL_SIZE * 1.5),
            (SCREEN_WIDTH - CELL_SIZE * 1.5, CELL_SIZE * 1.5),
            (SCREEN_WIDTH - CELL_SIZE * 1.5, SCREEN_HEIGHT - CELL_SIZE * 1.5)
        ]
        self.x, self.y = random.choice(corners)
        self.speed = GHOST_SPEED
        self.scatter_corner = random.choice(corners)  # Assign a corner to scatter to

    def get_grid_pos(self, x, y):
        return (int(y // CELL_SIZE), int(x // CELL_SIZE))

    def get_valid_neighbors(self, pos):
        row, col = pos
        neighbors = []
        for dr, dc in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
            new_row, new_col = row + dr, col + dc
            if (0 <= new_row < len(MAZE) and 
                0 <= new_col < len(MAZE[0]) and 
                MAZE[new_row][new_col] == 0):
                neighbors.append((new_row, new_col))
        return neighbors

    def find_path_to_player(self, player_x, player_y):
        start = self.get_grid_pos(self.x, self.y)
        goal = self.get_grid_pos(player_x, player_y)
        
        if start == goal:
            return []

        queue = [(start, [])]
        visited = {start}
        
        while queue:
            current, path = queue.pop(0)
            
            for next_pos in self.get_valid_neighbors(current):
                if next_pos not in visited:
                    visited.add(next_pos)
                    new_path = path + [next_pos]
                    if next_pos == goal:
                        return new_path
                    queue.append((next_pos, new_path))
        
        return []

    def move(self, player_x, player_y):
        # Update chase/scatter mode
        self.chase_counter += 1
        if self.chase_mode and self.chase_counter >= self.chase_time:
            self.chase_mode = False
            self.chase_counter = 0
        elif not self.chase_mode and self.chase_counter >= self.scatter_time:
            self.chase_mode = True
            self.chase_counter = 0

        # Update path periodically
        self.path_update_counter += 1
        if self.path_update_counter >= self.path_update_frequency:
            if self.chase_mode:
                self.path = self.find_path_to_player(player_x, player_y)
            else:
                # In scatter mode, head to scatter corner
                self.path = self.find_path_to_player(self.scatter_corner[0], self.scatter_corner[1])
            self.path_update_counter = 0

        if not self.path:
            return

        # Get next target position from path
        next_row, next_col = self.path[0]
        target_x = next_col * CELL_SIZE + CELL_SIZE // 2
        target_y = next_row * CELL_SIZE + CELL_SIZE // 2

        # Move towards target
        dx = target_x - self.x
        dy = target_y - self.y
        dist = (dx ** 2 + dy ** 2) ** 0.5
        
        if dist < self.speed:
            self.path.pop(0)
        else:
            if dist != 0:
                self.x += (dx / dist) * self.speed
                self.y += (dy / dist) * self.speed

    def draw(self):
        # Ghost body
        x, y = int(self.x), int(self.y)
        
        # Determine ghost color with wave effect
        if self.chase_mode:
            base_color = RED
        else:
            base_color = NEON_BLUE
            
        # Add wavey animation
        wave = math.sin(pygame.time.get_ticks() * 0.004 + self.wave_offset) * 0.2 + 0.8
        color = tuple(int(c * wave) for c in base_color)
        
        # Draw main body with anti-aliasing
        pygame.gfxdraw.filled_circle(screen, x, y, self.radius, color)
        pygame.gfxdraw.aacircle(screen, x, y, self.radius, color)
        
        # Draw bottom part (wavy)
        points = [(x - self.radius, y)]
        for i in range(6):
            wave_x = x - self.radius + (i * self.radius / 2)
            wave_y = y + math.sin(pygame.time.get_ticks() * 0.01 + i) * 3
            points.append((wave_x, wave_y + self.radius - 2))
        points.append((x + self.radius, y))
        
        pygame.gfxdraw.filled_polygon(screen, points, color)
        pygame.gfxdraw.aapolygon(screen, points, color)
        
        # Draw eyes
        eye_color = WHITE
        eye_radius = self.radius // 3
        
        # Left eye
        left_eye_x = x - self.radius // 2
        pygame.gfxdraw.filled_circle(screen, left_eye_x, y - 2, eye_radius, eye_color)
        
        # Right eye
        right_eye_x = x + self.radius // 2
        pygame.gfxdraw.filled_circle(screen, right_eye_x, y - 2, eye_radius, eye_color)
        
        # Pupils (follow player)
        pupil_color = BLACK
        pupil_radius = eye_radius // 2
        
        # Calculate pupil offset based on movement direction
        if self.path and len(self.path) > 0:
            next_pos = self.path[0]
            dx = (next_pos[1] * CELL_SIZE + CELL_SIZE // 2) - self.x
            dy = (next_pos[0] * CELL_SIZE + CELL_SIZE // 2) - self.y
            angle = math.atan2(dy, dx)
            pupil_offset_x = math.cos(angle) * 2
            pupil_offset_y = math.sin(angle) * 2
        else:
            pupil_offset_x = pupil_offset_y = 0
            
        # Draw pupils
        pygame.gfxdraw.filled_circle(screen, 
                                   int(left_eye_x + pupil_offset_x), 
                                   int(y - 2 + pupil_offset_y), 
                                   pupil_radius, pupil_color)
        pygame.gfxdraw.filled_circle(screen, 
                                   int(right_eye_x + pupil_offset_x), 
                                   int(y - 2 + pupil_offset_y), 
                                   pupil_radius, pupil_color)

class Pellet:
    def __init__(self, walls):
        self.walls = walls
        self.radius = 4
        self.respawn()
        self.glow_value = 0
        self.glow_increasing = True
        
    def respawn(self):
        while True:
            # Try to place pellet in a valid position
            col = random.randint(1, len(MAZE[0]) - 2)
            row = random.randint(1, len(MAZE) - 2)
            
            if MAZE[row][col] == 0:  # If it's an empty space
                self.x = col * CELL_SIZE + CELL_SIZE // 2
                self.y = row * CELL_SIZE + CELL_SIZE // 2
                
                # Check if it's not inside any wall
                pellet_rect = pygame.Rect(self.x - self.radius, self.y - self.radius,
                                        self.radius * 2, self.radius * 2)
                valid_position = True
                for wall in self.walls:
                    if pellet_rect.colliderect(wall.rect):
                        valid_position = False
                        break
                
                if valid_position:
                    break

    def draw(self):
        # Add pulsing glow effect
        if self.glow_increasing:
            self.glow_value += 0.1
            if self.glow_value >= 1:
                self.glow_increasing = False
        else:
            self.glow_value -= 0.1
            if self.glow_value <= 0:
                self.glow_increasing = True
                
        glow_radius = self.radius + 2 * self.glow_value
        glow_color = (255, 255, 255)  # Remove alpha channel
        
        # Draw glow
        pygame.gfxdraw.filled_circle(screen, int(self.x), int(self.y), 
                                   int(glow_radius), glow_color)
        # Draw pellet
        pygame.gfxdraw.filled_circle(screen, int(self.x), int(self.y), 
                                   self.radius, PELLET_COLOR)
        pygame.gfxdraw.aacircle(screen, int(self.x), int(self.y), 
                               self.radius, PELLET_COLOR)

def create_walls():
    walls = []
    for row in range(len(MAZE)):
        for col in range(len(MAZE[0])):
            if MAZE[row][col] == 1:
                walls.append(Wall(col * CELL_SIZE, row * CELL_SIZE, 
                                CELL_SIZE, CELL_SIZE))
    return walls

def draw_score(score):
    score_surface = SCORE_FONT.render(f'Score: {score}', True, WHITE)
    score_rect = score_surface.get_rect(topleft=(10, 10))
    
    # Draw shadow
    shadow_surface = SCORE_FONT.render(f'Score: {score}', True, (50, 50, 50))
    shadow_rect = shadow_surface.get_rect(topleft=(12, 12))
    screen.blit(shadow_surface, shadow_rect)
    
    # Draw text
    screen.blit(score_surface, score_rect)

def main():
    walls = create_walls()
    player = Player(walls)
    ghosts = [Ghost(walls) for _ in range(3)]
    pellets = [Pellet(walls) for _ in range(10)]
    
    running = True
    game_over = False
    
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and game_over:
                if event.key == pygame.K_SPACE:
                    # Reset game
                    player = Player(walls)
                    ghosts = [Ghost(walls) for _ in range(3)]
                    pellets = [Pellet(walls) for _ in range(10)]
                    game_over = False
        
        if not game_over:
            # Game logic
            player.move()
            
            # Move ghosts
            for ghost in ghosts:
                ghost.move(player.x, player.y)
                
                # Check collision with player
                dist = ((ghost.x - player.x) ** 2 + (ghost.y - player.y) ** 2) ** 0.5
                if dist < player.radius + ghost.radius:
                    player.die()
                    running = False

            # Check pellet collection
            for pellet in pellets[:]:
                dist = ((pellet.x - player.x) ** 2 + (pellet.y - player.y) ** 2) ** 0.5
                if dist < player.radius + pellet.radius:
                    player.collect_pellet()
                    pellets.remove(pellet)
                    if len(pellets) == 0:
                        running = False
        
        # Drawing
        screen.fill(BACKGROUND_COLOR)
        
        # Draw walls
        for wall in walls:
            wall.draw()
        
        # Draw game objects
        for pellet in pellets:
            pellet.draw()
        for ghost in ghosts:
            ghost.draw()
        player.draw()
        
        # Draw score
        draw_score(player.score)
        
        # Draw game over screen
        if game_over:
            # Create semi-transparent overlay
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            overlay.fill((0, 0, 0))
            overlay.set_alpha(128)
            screen.blit(overlay, (0, 0))
            
            # Draw game over text
            game_over_text = GAME_FONT.render('Game Over!', True, WHITE)
            score_text = GAME_FONT.render(f'Final Score: {player.score}', True, WHITE)
            restart_text = SCORE_FONT.render('Press SPACE to restart', True, WHITE)
            
            screen.blit(game_over_text, 
                       game_over_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 50)))
            screen.blit(score_text, 
                       score_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 10)))
            screen.blit(restart_text, 
                       restart_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 70)))
        
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

if __name__ == "__main__":
    MAZE = [
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
        [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1],
        [1, 0, 1, 1, 0, 1, 0, 1, 1, 1, 1, 1, 1, 0, 1, 0, 1, 1, 0, 1],
        [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
        [1, 0, 1, 1, 0, 1, 1, 1, 0, 1, 1, 0, 1, 1, 1, 0, 1, 1, 0, 1],
        [1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1],
        [1, 1, 1, 1, 0, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1, 1, 1, 1],
        [1, 1, 1, 1, 0, 1, 0, 1, 0, 0, 0, 0, 1, 0, 1, 0, 1, 1, 1, 1],
        [1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1],
        [1, 0, 1, 1, 0, 1, 1, 1, 0, 1, 1, 0, 1, 1, 1, 0, 1, 1, 0, 1],
        [1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1],
        [1, 1, 0, 1, 0, 1, 0, 1, 1, 1, 1, 1, 1, 0, 1, 0, 1, 0, 1, 1],
        [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1],
        [1, 0, 1, 1, 1, 1, 1, 1, 0, 1, 1, 0, 1, 1, 1, 1, 1, 1, 0, 1],
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
    ]
    main()
