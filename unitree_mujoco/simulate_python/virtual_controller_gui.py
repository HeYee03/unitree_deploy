"""
Virtual Controller GUI - Pygame-based virtual joystick controller
Provides clickable FSM buttons and two draggable virtual joystick pads.
"""

import pygame
import math


# Colors
BG_COLOR = (25, 25, 35)
PANEL_COLOR = (35, 35, 50)
STICK_BG = (50, 50, 70)
STICK_RING = (80, 80, 110)
STICK_KNOB = (0, 200, 120)
STICK_KNOB_ACTIVE = (0, 255, 150)
BTN_STAND = (40, 120, 200)
BTN_STAND_HOVER = (60, 150, 240)
BTN_WALK = (30, 180, 80)
BTN_WALK_HOVER = (50, 220, 100)
BTN_STOP = (200, 50, 50)
BTN_STOP_HOVER = (240, 70, 70)
TEXT_COLOR = (200, 210, 220)
TEXT_DIM = (120, 130, 140)
LABEL_COLOR = (160, 170, 180)
ACTIVE_COLOR = (0, 255, 120)
VALUE_BAR_BG = (40, 40, 60)
VALUE_BAR_POS = (0, 180, 100)
VALUE_BAR_NEG = (180, 80, 0)


class VirtualStick:
    """A draggable circular joystick pad."""

    def __init__(self, cx, cy, radius, label=""):
        self.cx = cx
        self.cy = cy
        self.radius = radius
        self.knob_radius = radius // 3
        self.label = label
        self.dx = 0.0  # -1 to 1
        self.dy = 0.0  # -1 to 1
        self.dragging = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = event.pos
            dist = math.hypot(mx - self.cx, my - self.cy)
            if dist <= self.radius:
                self.dragging = True
                self._update_from_mouse(mx, my)
        elif event.type == pygame.MOUSEBUTTONUP:
            if self.dragging:
                self.dragging = False
                self.dx = 0.0
                self.dy = 0.0
        elif event.type == pygame.MOUSEMOTION:
            if self.dragging:
                self._update_from_mouse(*event.pos)

    def _update_from_mouse(self, mx, my):
        dx = (mx - self.cx) / self.radius
        dy = (my - self.cy) / self.radius  # pygame y is inverted
        dist = math.hypot(dx, dy)
        if dist > 1.0:
            dx /= dist
            dy /= dist
        self.dx = max(-1.0, min(1.0, dx))
        self.dy = max(-1.0, min(1.0, -dy))  # invert y: up = positive

    def draw(self, surface, font):
        # Background circle
        pygame.draw.circle(surface, STICK_BG, (self.cx, self.cy), self.radius)
        # Crosshair
        pygame.draw.line(
            surface,
            STICK_RING,
            (self.cx - self.radius, self.cy),
            (self.cx + self.radius, self.cy),
            1,
        )
        pygame.draw.line(
            surface,
            STICK_RING,
            (self.cx, self.cy - self.radius),
            (self.cx, self.cy + self.radius),
            1,
        )
        # Ring
        pygame.draw.circle(surface, STICK_RING, (self.cx, self.cy), self.radius, 2)
        # Knob
        knob_x = int(self.cx + self.dx * self.radius * 0.8)
        knob_y = int(self.cy - self.dy * self.radius * 0.8)  # invert y for drawing
        color = STICK_KNOB_ACTIVE if self.dragging else STICK_KNOB
        pygame.draw.circle(surface, color, (knob_x, knob_y), self.knob_radius)
        pygame.draw.circle(
            surface, (255, 255, 255), (knob_x, knob_y), self.knob_radius, 2
        )
        # Label
        label_surf = font.render(self.label, True, LABEL_COLOR)
        surface.blit(
            label_surf,
            (self.cx - label_surf.get_width() // 2, self.cy + self.radius + 8),
        )


class GUIButton:
    """A clickable GUI button that triggers a timed action."""

    def __init__(self, x, y, w, h, text, color, hover_color):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.pressed = False
        self.press_timer = 0  # frames remaining

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                self.pressed = True
                self.press_timer = 60  # hold for ~60 frames (~3s at 20fps)
        elif event.type == pygame.MOUSEBUTTONUP:
            pass  # button stays pressed for timer duration

    def update(self):
        if self.press_timer > 0:
            self.press_timer -= 1
            self.pressed = True
        else:
            self.pressed = False

    def draw(self, surface, font):
        color = self.hover_color if self.pressed else self.color
        # Draw rounded rect
        pygame.draw.rect(surface, color, self.rect, border_radius=8)
        if self.pressed:
            pygame.draw.rect(surface, (255, 255, 255), self.rect, 2, border_radius=8)
        else:
            pygame.draw.rect(surface, (80, 80, 100), self.rect, 1, border_radius=8)
        # Text
        text_surf = font.render(self.text, True, (255, 255, 255))
        tx = self.rect.centerx - text_surf.get_width() // 2
        ty = self.rect.centery - text_surf.get_height() // 2
        surface.blit(text_surf, (tx, ty))


class VirtualControllerGUI:
    """Main virtual controller GUI with buttons, joysticks, and keyboard input."""

    def __init__(self, width=800, height=420):
        self.width = width
        self.height = height
        self.screen = None
        self.font = None
        self.font_sm = None
        self.font_lg = None

        # Joystick pads
        stick_y = height // 2 - 20
        self.left_stick = VirtualStick(160, stick_y, 90, "Move (WASD)")
        self.right_stick = VirtualStick(640, stick_y, 90, "Turn (QEZX)")

        # FSM Buttons
        btn_y = height - 75
        btn_w, btn_h = 140, 50
        self.btn_stand = GUIButton(
            240, btn_y, btn_w, btn_h, "▲ Stand", BTN_STAND, BTN_STAND_HOVER
        )
        self.btn_walk = GUIButton(
            400, btn_y, btn_w, btn_h, "▶ Walk", BTN_WALK, BTN_WALK_HOVER
        )
        self.btn_stop = GUIButton(
            560, btn_y, btn_w, btn_h, "■ Stop", BTN_STOP, BTN_STOP_HOVER
        )

        self.buttons = [self.btn_stand, self.btn_walk, self.btn_stop]

        # Output state (matches WirelessController format)
        self.state = {
            "lx": 0.0,
            "ly": 0.0,
            "rx": 0.0,
            "ry": 0.0,
            "L2": 0,
            "R1": 0,
            "L1": 0,
            "R2": 0,
            "A": 0,
            "B": 0,
            "X": 0,
            "Y": 0,
            "up": 0,
            "down": 0,
            "left": 0,
            "right": 0,
            "start": 0,
            "select": 0,
        }
        self.running = True

    def init_display(self):
        """Initialize pygame display. Must be called from main thread."""
        self.screen = pygame.display.set_mode(
            (self.width, self.height), pygame.SWSURFACE
        )
        pygame.display.set_caption("🎮 Virtual Controller")
        pygame.font.init()
        self.font = pygame.font.SysFont("monospace", 18)
        self.font_sm = pygame.font.SysFont("monospace", 14)
        self.font_lg = pygame.font.SysFont("monospace", 22, bold=True)

    def process_events(self):
        """Process pygame events. Call from main thread."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return
            self.left_stick.handle_event(event)
            self.right_stick.handle_event(event)
            for btn in self.buttons:
                btn.handle_event(event)

        # Update button timers
        for btn in self.buttons:
            btn.update()

        # Read keyboard
        keys = pygame.key.get_pressed()

        # --- Build state ---
        state = self.state

        # Reset axes
        state["lx"] = 0.0
        state["ly"] = 0.0
        state["rx"] = 0.0

        # Keyboard: WASD = translation
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            state["ly"] = 1.0
        elif keys[pygame.K_s] or keys[pygame.K_DOWN]:
            state["ly"] = -1.0

        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            state["lx"] = -1.0
        elif keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            state["lx"] = 1.0

        # Keyboard: QEZX = turning (rx axis)
        if keys[pygame.K_q] or keys[pygame.K_z]:
            state["rx"] = -1.0
        elif keys[pygame.K_e] or keys[pygame.K_x]:
            state["rx"] = 1.0

        # Combine with mouse joystick (keyboard overrides if pressed)
        if state["lx"] == 0 and state["ly"] == 0:
            state["lx"] = self.left_stick.dx
            state["ly"] = self.left_stick.dy
        if state["rx"] == 0:
            state["rx"] = self.right_stick.dx

        # Buttons → FSM commands (two-phase trigger)
        # C++ UnitreeJoystick LT is an Axis with smooth=0.03.
        # It needs ~23 iterations at 500Hz to ramp from 0→0.5 (threshold).
        # We must send the "hold" key (L2/R1) first, then delay the
        # "trigger" key (up/X/B) so on_pressed fires AFTER the Axis ramps up.
        # At 20fps GUI, 15 frames delay = 750ms = 375 publish cycles, plenty.
        DELAY_FRAMES = 15  # frames before sending the trigger key

        # Reset all FSM buttons first
        state["L2"] = 0
        state["R1"] = 0
        state["up"] = 0
        state["X"] = 0
        state["B"] = 0

        # Stand = L2 + Up (L2 first, Up delayed)
        if self.btn_stand.pressed:
            state["L2"] = 1  # Always send L2 while pressed
            elapsed = 60 - self.btn_stand.press_timer
            if elapsed >= DELAY_FRAMES:
                state["up"] = 1  # Send Up only after delay

        # Walk = R1 + X (R1 first, X delayed)
        if self.btn_walk.pressed:
            state["R1"] = 1
            elapsed = 60 - self.btn_walk.press_timer
            if elapsed >= DELAY_FRAMES:
                state["X"] = 1

        # Stop = L2 + B (L2 first, B delayed)
        if self.btn_stop.pressed:
            state["L2"] = 1
            elapsed = 60 - self.btn_stop.press_timer
            if elapsed >= DELAY_FRAMES:
                state["B"] = 1

    def render(self):
        """Render the GUI. Call from main thread."""
        if not self.screen:
            return

        self.screen.fill(BG_COLOR)

        # Title bar
        title = self.font_lg.render("Virtual Controller", True, TEXT_COLOR)
        self.screen.blit(title, (self.width // 2 - title.get_width() // 2, 8))

        # Draw sticks
        self.left_stick.draw(self.screen, self.font_sm)
        self.right_stick.draw(self.screen, self.font_sm)

        # Draw value bars between sticks
        self._draw_value_display(self.screen, self.width // 2, 70)

        # Draw buttons
        for btn in self.buttons:
            btn.draw(self.screen, self.font)

        # Keyboard hints
        hints = "Keyboard: WASD=Move  QEZX=Turn"
        hint_surf = self.font_sm.render(hints, True, TEXT_DIM)
        self.screen.blit(
            hint_surf, (self.width // 2 - hint_surf.get_width() // 2, self.height - 20)
        )

        try:
            pygame.display.update()
        except Exception:
            pass

    def _draw_value_display(self, surface, cx, y):
        """Draw current axis values as bars."""
        state = self.state
        bar_w = 120
        bar_h = 14
        gap = 22

        labels = [
            ("FWD/BWD", state["ly"]),
            ("LEFT/RIGHT", state["lx"]),
            ("TURN", state["rx"]),
        ]

        for i, (label, val) in enumerate(labels):
            by = y + i * gap
            # Label
            lbl = self.font_sm.render(label, True, LABEL_COLOR)
            surface.blit(lbl, (cx - bar_w // 2 - lbl.get_width() - 8, by))
            # Bar background
            bar_rect = pygame.Rect(cx - bar_w // 2, by, bar_w, bar_h)
            pygame.draw.rect(surface, VALUE_BAR_BG, bar_rect, border_radius=3)
            # Bar fill
            fill_w = int(abs(val) * bar_w // 2)
            if val > 0:
                fill_rect = pygame.Rect(cx, by, fill_w, bar_h)
                pygame.draw.rect(surface, VALUE_BAR_POS, fill_rect, border_radius=3)
            elif val < 0:
                fill_rect = pygame.Rect(cx - fill_w, by, fill_w, bar_h)
                pygame.draw.rect(surface, VALUE_BAR_NEG, fill_rect, border_radius=3)
            # Center line
            pygame.draw.line(surface, (100, 100, 120), (cx, by), (cx, by + bar_h), 1)
            # Value text
            val_txt = self.font_sm.render(
                f"{val:+.2f}", True, ACTIVE_COLOR if abs(val) > 0.01 else TEXT_DIM
            )
            surface.blit(val_txt, (cx + bar_w // 2 + 6, by))

    def get_state(self):
        """Return current controller state dict."""
        return self.state.copy()
