import pyMeow as pm
import requests
import time
import os
import ctypes
import sys
import random
import string
from ctypes import wintypes

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

PURPLE = pm.get_color("#9966cc")
WHITE = pm.get_color("#FFFFFF")
RED = pm.get_color("#FF4747")
BLUE = pm.get_color("#4785FF")
GREEN = pm.get_color("#47FF47")
BLACK = pm.get_color("#0B0C0E")
YELLOW = pm.get_color("#FFFF47")
ORANGE = pm.get_color("#FFA500")
PINK = pm.get_color("#FF47FF")
CYAN = pm.get_color("#47FFFF")
GRAY = pm.get_color("#888888")

class Mouse:
    x = 0
    y = 0
    pressed = False
    last_pressed = False

class Menu:
    x = 300
    y = 300
    show = False
    time = 0
    dragging = False
    offset_x = 0
    offset_y = 0
    width = 300
    height = 570
    color_picker_active = False
    color_picker_target = None
    color_picker_x = 0
    color_picker_y = 0

class Config:
    enemy_box = True
    enemy_box_color = GREEN
    enemy_health = True
    enemy_health_color = GREEN
    enemy_health_bg_color = RED
    enemy_line = False
    enemy_line_color = GREEN
    enemy_name = True
    enemy_name_color = WHITE
    enemy_distance = True
    enemy_distance_color = WHITE
    enemy_weapon = False
    enemy_weapon_color = WHITE
    enemy_skeleton = False
    enemy_skeleton_color = GREEN
    show_teammates = False
    enemy_color = GREEN
    friend_color = BLUE

    available_colors = [
        {"name": "green", "color": GREEN},
        {"name": "blue", "color": BLUE},
        {"name": "red", "color": RED},
        {"name": "purple", "color": PURPLE},
        {"name": "yellow", "color": YELLOW},
        {"name": "orange", "color": ORANGE},
        {"name": "pink", "color": PINK},
        {"name": "cyan", "color": CYAN},
        {"name": "white", "color": WHITE}
    ]

    watermark = True
    only_render_when_focused = True

def is_cs2_focused():
    foreground_window = user32.GetForegroundWindow()
    if not foreground_window:
        return False
    
    process_id = wintypes.DWORD()
    thread_id = user32.GetWindowThreadProcessId(foreground_window, ctypes.byref(process_id))
    
    try:
        handle = kernel32.OpenProcess(0x0400 | 0x0010, False, process_id.value)
        if handle:
            name_buffer = ctypes.create_unicode_buffer(1024)
            name_size = ctypes.c_ulong(1024)
            if kernel32.QueryFullProcessImageNameW(handle, 0, name_buffer, ctypes.byref(name_size)):
                process_name = name_buffer.value.lower()
                kernel32.CloseHandle(handle)
                return "cs2.exe" in process_name
            kernel32.CloseHandle(handle)
    except Exception:
        pass
    
    return False

class Entity:
    def __init__(self, entity_controller, entity_pawn, process):
        self.entity_controller = entity_controller
        self.entity_pawn = entity_pawn
        self.process = process

    def health(self):
        return pm.r_int(self.process, self.entity_pawn + m_iHealth)
    
    def armor(self):
        return pm.r_int(self.process, self.entity_pawn + m_ArmorValue)

    def team(self):
        return pm.r_int(self.process, self.entity_pawn + m_iTeamNum)

    def name(self):
        return pm.r_string(self.process, self.entity_controller + m_iszPlayerName)
    
    def weapon(self):
        current = pm.r_int64(self.process, self.entity_pawn + m_pClippingWeapon)
        if current == 0:
            return ""
        
        try:
            index = pm.r_int16(self.process, current + m_AttributeManager + m_Item + m_iItemDefinitionIndex)
            weapon_name = get_weapon_name(index)
            return weapon_name
        except Exception:
            return ""

    def pos(self):
        return pm.r_vec3(self.process, self.entity_pawn + m_vOldOrigin)
    
    def bone_pos(self, index):
        scene = pm.r_int64(self.process, self.entity_pawn + m_pGameSceneNode)
        bone = pm.r_int64(self.process, scene + m_pBoneArray)
        return pm.r_vec3(self.process, bone + index * 32)

    def world_to_screen(self, view_matrix):
        try:
            self.pos_2d = pm.world_to_screen(view_matrix, self.pos(), 1)
            self.head_pos_2d = pm.world_to_screen(view_matrix, self.bone_pos(6), 1)
            self.neck = pm.world_to_screen(view_matrix, self.bone_pos(5), 1)
            self.left_feet = pm.world_to_screen(view_matrix, self.bone_pos(27), 1)
            self.right_feet = pm.world_to_screen(view_matrix, self.bone_pos(24), 1)
            self.waist = pm.world_to_screen(view_matrix, self.bone_pos(0), 1)
            self.left_knees = pm.world_to_screen(view_matrix, self.bone_pos(26), 1)
            self.right_knees = pm.world_to_screen(view_matrix, self.bone_pos(23), 1)
            self.left_hand = pm.world_to_screen(view_matrix, self.bone_pos(16), 1)
            self.right_hand = pm.world_to_screen(view_matrix, self.bone_pos(11), 1)
            self.left_arm = pm.world_to_screen(view_matrix, self.bone_pos(14), 1)
            self.right_arm = pm.world_to_screen(view_matrix, self.bone_pos(9), 1)
            self.left_shoulder = pm.world_to_screen(view_matrix, self.bone_pos(13), 1)
            self.right_shoulder = pm.world_to_screen(view_matrix, self.bone_pos(8), 1)
            return True
        except Exception:
            return False

class Entities:
    def __init__(self, process, module):
        self.process = process
        self.module = module

    def get_all_entities(self):
        entities = []
        local_player_controller = pm.r_int64(self.process, self.module + dwLocalPlayerController)

        for entity in range(1, 65):
            try:
                entity_list = pm.r_int64(self.process, self.module + dwEntityList)
                entity_entry = pm.r_int64(self.process, entity_list + (8 * (entity & 0x7FFF) >> 9) + 16)
                entity_controller = pm.r_int64(self.process, entity_entry + 120 * (entity & 0x1FF))

                if entity_controller == local_player_controller or entity_controller == 0:
                    continue
                
                entity_controller_pawn = pm.r_int64(self.process, entity_controller + m_hPlayerPawn)
                entity_list_ptr = pm.r_int64(self.process, entity_list + 8 * ((entity_controller_pawn & 0x7FFF) >> 9) + 16)
                entity_pawn = pm.r_int64(self.process, entity_list_ptr + 120 * (entity_controller_pawn & 0x1FF))
                
                if entity_pawn == 0:
                    continue
                
                entities.append(Entity(entity_controller, entity_pawn, self.process))
            except Exception:
                continue

        return entities

def clean_text(text):
    return ''.join(char for char in text if char.isprintable())

def get_weapon_name(index):
    weapons = {
        1: "Desert Eagle",
        2: "Dual Berettas",
        3: "Five-SeveN",
        4: "Glock-18",
        7: "AK-47",
        8: "AUG",
        9: "AWP",
        10: "FAMAS",
        11: "G3SG1",
        13: "Galil AR",
        14: "M249",
        16: "M4A4",
        17: "MAC-10",
        19: "P90",
        20: "Repulsor",
        23: "MP5-SD",
        24: "UMP-45",
        25: "XM1014",
        26: "PP-Bizon",
        27: "MAG-7",
        28: "Negev",
        29: "Sawed-Off",
        30: "Tec-9",
        31: "Zeus x27",
        32: "P2000",
        33: "MP7",
        34: "MP9",
        35: "Nova",
        36: "P250",
        38: "SCAR-20",
        39: "SG 553",
        40: "SSG 08",
        41: "Knife",
        42: "Knife",
        43: "Knife",
        44: "Knife",
        45: "Knife",
        46: "Knife",
        47: "Knife",
        48: "Knife",
        49: "Knife",
        50: "Knife",
        51: "Knife",
        52: "Knife",
        54: "Knife",
        55: "Knife",
        56: "Knife",
        57: "Knife",
        58: "Knife",
        59: "Knife",
        60: "M4A1-S",
        61: "USP-S",
        63: "CZ75-Auto",
        64: "Revolver",
        512: "Breach Charge",
        516: "Decoy Grenade",
        517: "Flashbang",
        518: "HE Grenade",
        519: "Smoke Grenade",
        520: "Molotov",
        522: "C4"
    }
    return weapons.get(index, "Unknown")

def calculate_distance(pos1, pos2):
    return ((pos1["x"] - pos2["x"])**2 + (pos1["y"] - pos2["y"])**2 + (pos1["z"] - pos2["z"])**2)**0.5

def update_mouse():
    pos = pm.mouse_position()
    Mouse.x = pos["x"]
    Mouse.y = pos["y"]
    
    Mouse.last_pressed = Mouse.pressed
    Mouse.pressed = pm.mouse_pressed()

def toggle_menu():
    if pm.key_pressed(vKey=0x2D):
        current_time = time.time()
        if current_time - Menu.time > 0.3:
            Menu.show = not Menu.show
            Menu.time = current_time
            Menu.color_picker_active = False
            pm.toggle_mouse()

def drag_menu():
    if Mouse.pressed and Menu.show:
        if not Menu.dragging and Menu.x <= Mouse.x <= Menu.x + Menu.width and Menu.y <= Mouse.y <= Menu.y + 30:
            Menu.dragging = True
            Menu.offset_x = Mouse.x - Menu.x
            Menu.offset_y = Mouse.y - Menu.y

        if Menu.dragging:
            Menu.x = Mouse.x - Menu.offset_x
            Menu.y = Mouse.y - Menu.offset_y

    if not Mouse.pressed:
        Menu.dragging = False

class ESP:
    def __init__(self, process, module):
        self.process = process
        self.module = module
        self.entities = Entities(self.process, self.module)
        self.cs2_focused = True
        self.last_focus_check = 0
        
    def update(self):
        current_time = time.time()
        if current_time - self.last_focus_check > 0.5:
            self.cs2_focused = is_cs2_focused()
            self.last_focus_check = current_time
            
        if Config.only_render_when_focused and not self.cs2_focused and not Menu.show:
            return
            
        try:
            view_matrix = pm.r_floats(self.process, self.module + dwViewMatrix, 16)
            if not view_matrix:
                return
                
            local_player_controller = pm.r_int64(self.process, self.module + dwLocalPlayerController)
            if local_player_controller == 0:
                return
                
            local_player_team = pm.r_int(self.process, local_player_controller + m_iTeamNum)
            if local_player_team == 0:
                return
                
            local_player_pawn = pm.r_int64(self.process, self.module + dwLocalPlayerPawn)
            if local_player_pawn != 0:
                local_player_pos = pm.r_vec3(self.process, local_player_pawn + m_vOldOrigin)
            else:
                local_player_pos = {"x": 0, "y": 0, "z": 0}
            
            self._process_entities(view_matrix, local_player_team, local_player_pos)
                
        except Exception:
            pass
            
    def _process_entities(self, view_matrix, local_player_team, local_player_pos):
        entities = self.entities.get_all_entities()
        
        for entity in entities:
            try:
                if not entity or not entity.entity_pawn or not entity.entity_controller:
                    continue
                    
                health = entity.health()
                if health <= 0 or health > 100:
                    continue
                    
                if not entity.world_to_screen(view_matrix):
                    continue
                    
                head_to_foot = entity.pos_2d["y"] - entity.head_pos_2d["y"]
                box_width = head_to_foot / 2
                box_height = head_to_foot * 1.2
                box_x = entity.head_pos_2d["x"] - box_width / 2
                box_y = entity.head_pos_2d["y"] - box_height * 0.05
                corner_length = min(box_width, box_height) * 0.2
                
                if box_width <= 0 or box_height <= 0:
                    continue
                    
                name = clean_text(entity.name())
                if not name:
                    continue
                    
                distance = int(calculate_distance(local_player_pos, entity.pos()) / 50)

                is_enemy = entity.team() != local_player_team
                
                if not is_enemy and not Config.show_teammates:
                    continue
                
                main_color = Config.enemy_color if is_enemy else Config.friend_color
                
                self._draw_esp_features(entity, box_x, box_y, box_width, box_height, main_color, distance, name, is_enemy)
                
            except Exception:
                continue
                
    def _draw_esp_features(self, entity, box_x, box_y, box_width, box_height, main_color, distance, name, is_enemy):
        if Config.enemy_skeleton:
            pm.draw_circle_lines(
                centerX=entity.head_pos_2d["x"],
                centerY=entity.head_pos_2d["y"],
                radius=box_width / 4,
                color=pm.fade_color(main_color, 0.7)
            )
            self._draw_skeleton(entity, main_color)

        if Config.enemy_box:
            pm.draw_rectangle_rounded_lines(
                posX=box_x,
                posY=box_y,
                width=box_width,
                height=box_height,
                roundness=0.05,
                segments=1,
                color=pm.fade_color(main_color, 0.7),
                lineThick=1.2
            )

        if Config.enemy_line:
            pm.draw_line(
                startPosX=pm.get_screen_width() / 2,
                startPosY=pm.get_screen_height() - 100,
                endPosX=entity.pos_2d["x"],
                endPosY=entity.pos_2d["y"],
                color=pm.fade_color(main_color, 0.7),
                thick=0.5
            )

        if Config.enemy_name:
            name_width = pm.measure_text(text=name, fontSize=12)
            pm.draw_text(
                text=name,
                posX=entity.head_pos_2d["x"] - (name_width / 2),
                posY=entity.head_pos_2d["y"] - 15,
                fontSize=12,
                color=Config.enemy_name_color
            )

        if Config.enemy_distance:
            distance_text = f"{distance}m"
            distance_width = pm.measure_text(text=distance_text, fontSize=10)
            pm.draw_text(
                text=distance_text,
                posX=entity.pos_2d["x"] - (distance_width / 2),
                posY=entity.pos_2d["y"] + 5,
                fontSize=10,
                color=Config.enemy_distance_color
            )

        if Config.enemy_weapon:
            weapon_text = entity.weapon()
            weapon_width = pm.measure_text(text=weapon_text, fontSize=10)
            pm.draw_text(
                text=weapon_text,
                posX=entity.head_pos_2d["x"] - (weapon_width / 2),
                posY=entity.head_pos_2d["y"] + box_height + 15,
                fontSize=10,
                color=Config.enemy_weapon_color
            )

        if Config.enemy_health:
            pm.draw_rectangle(
                posX=box_x - 8,
                posY=box_y,
                width=2,
                height=box_height,
                color=Config.enemy_health_bg_color
            )

            pm.draw_rectangle(
                posX=box_x - 8,
                posY=box_y + (box_height * (100 - entity.health()) / 100),
                width=2,
                height=box_height * (entity.health() / 100),
                color=Config.enemy_health_color
            )
            
    def _draw_skeleton(self, entity, main_color):
        skeleton_points = [
            (entity.neck["x"], entity.neck["y"], entity.right_shoulder["x"], entity.right_shoulder["y"]),
            (entity.neck["x"], entity.neck["y"], entity.left_shoulder["x"], entity.left_shoulder["y"]),
            (entity.left_arm["x"], entity.left_arm["y"], entity.left_shoulder["x"], entity.left_shoulder["y"]),
            (entity.right_arm["x"], entity.right_arm["y"], entity.right_shoulder["x"], entity.right_shoulder["y"]),
            (entity.right_arm["x"], entity.right_arm["y"], entity.right_hand["x"], entity.right_hand["y"]),
            (entity.left_arm["x"], entity.left_arm["y"], entity.left_hand["x"], entity.left_hand["y"]),
            (entity.neck["x"], entity.neck["y"], entity.waist["x"], entity.waist["y"]),
            (entity.right_knees["x"], entity.right_knees["y"], entity.waist["x"], entity.waist["y"]),
            (entity.left_knees["x"], entity.left_knees["y"], entity.waist["x"], entity.waist["y"]),
            (entity.left_knees["x"], entity.left_knees["y"], entity.left_feet["x"], entity.left_feet["y"]),
            (entity.right_knees["x"], entity.right_knees["y"], entity.right_feet["x"], entity.right_feet["y"])
        ]
        
        for bone in skeleton_points:
            pm.draw_line(
                startPosX=bone[0], 
                startPosY=bone[1], 
                endPosX=bone[2], 
                endPosY=bone[3], 
                color=pm.fade_color(main_color, 0.7), 
                thick=1.0
            )

def draw_menu():
    if not Menu.show:
        return
    
    if Mouse.pressed and not Mouse.last_pressed:
        if Menu.color_picker_active:
            picker_width = 180
            picker_height = 80
            if not (Menu.color_picker_x <= Mouse.x <= Menu.color_picker_x + picker_width and 
                   Menu.color_picker_y <= Mouse.y <= Menu.color_picker_y + picker_height):
                close_picker = True
                
                enemy_color_y = Menu.y + 45 + 25 + 25*7 + 25 + 25
                if (Menu.x + Menu.width - 80 <= Mouse.x <= Menu.x + Menu.width - 20 and 
                   enemy_color_y + 2 <= Mouse.y <= enemy_color_y + 17):
                    Menu.color_picker_target = "enemy"
                    Menu.color_picker_x = Menu.x + 100
                    Menu.color_picker_y = enemy_color_y + 25
                    close_picker = False
                
                teammate_color_y = enemy_color_y + 25
                if (Menu.x + Menu.width - 80 <= Mouse.x <= Menu.x + Menu.width - 20 and 
                   teammate_color_y + 2 <= Mouse.y <= teammate_color_y + 17):
                    Menu.color_picker_target = "teammate"
                    Menu.color_picker_x = Menu.x + 100
                    Menu.color_picker_y = teammate_color_y + 25
                    close_picker = False
                
                if close_picker:
                    Menu.color_picker_active = False
        
    pm.draw_rectangle_rounded(
        posX=Menu.x,
        posY=Menu.y,
        width=Menu.width,
        height=Menu.height,
        roundness=0.05,
        segments=8,
        color=pm.fade_color(BLACK, 0.85)
    )
    
    pm.draw_rectangle_rounded(
        posX=Menu.x,
        posY=Menu.y,
        width=Menu.width,
        height=30,
        roundness=0.05,
        segments=8,
        color=pm.fade_color(BLACK, 0.9)
    )
    
    pm.draw_rectangle(
        posX=Menu.x,
        posY=Menu.y + 30,
        width=Menu.width,
        height=2,
        color=PURPLE
    )
    
    title_text = "cs2 simple esp"
    title_width = pm.measure_text(text=title_text, fontSize=16)
    pm.draw_text(
        text=title_text,
        posX=Menu.x + (Menu.width - title_width) / 2,
        posY=Menu.y + 7,
        fontSize=16,
        color=WHITE
    )
    
    section_y = Menu.y + 45
    pm.draw_text(
        text="esp settings",
        posX=Menu.x + 15,
        posY=section_y,
        fontSize=14,
        color=PURPLE
    )
    
    option_y = section_y + 25
    
    pm.draw_text(
        text="box esp",
        posX=Menu.x + 15,
        posY=option_y,
        fontSize=12,
        color=WHITE
    )
    draw_toggle(Menu.x + Menu.width - 40, option_y, Config.enemy_box, "enemy_box")
    option_y += 25
    
    pm.draw_text(
        text="health bars",
        posX=Menu.x + 15,
        posY=option_y,
        fontSize=12,
        color=WHITE
    )
    draw_toggle(Menu.x + Menu.width - 40, option_y, Config.enemy_health, "enemy_health")
    option_y += 25
    
    pm.draw_text(
        text="name esp",
        posX=Menu.x + 15,
        posY=option_y,
        fontSize=12,
        color=WHITE
    )
    draw_toggle(Menu.x + Menu.width - 40, option_y, Config.enemy_name, "enemy_name")
    option_y += 25
    
    pm.draw_text(
        text="distance",
        posX=Menu.x + 15,
        posY=option_y,
        fontSize=12,
        color=WHITE
    )
    draw_toggle(Menu.x + Menu.width - 40, option_y, Config.enemy_distance, "enemy_distance")
    option_y += 25
    
    pm.draw_text(
        text="skeleton",
        posX=Menu.x + 15,
        posY=option_y,
        fontSize=12,
        color=WHITE
    )
    draw_toggle(Menu.x + Menu.width - 40, option_y, Config.enemy_skeleton, "enemy_skeleton")
    option_y += 25
    
    pm.draw_text(
        text="weapon",
        posX=Menu.x + 15,
        posY=option_y,
        fontSize=12,
        color=WHITE
    )
    draw_toggle(Menu.x + Menu.width - 40, option_y, Config.enemy_weapon, "enemy_weapon")
    option_y += 25
    
    pm.draw_text(
        text="line esp",
        posX=Menu.x + 15,
        posY=option_y,
        fontSize=12,
        color=WHITE
    )
    draw_toggle(Menu.x + Menu.width - 40, option_y, Config.enemy_line, "enemy_line")
    option_y += 25
    
    pm.draw_text(
        text="show teammates",
        posX=Menu.x + 15,
        posY=option_y,
        fontSize=12,
        color=WHITE
    )
    draw_toggle(Menu.x + Menu.width - 40, option_y, Config.show_teammates, "show_teammates")
    option_y += 25
    
    pm.draw_text(
        text="color settings",
        posX=Menu.x + 15,
        posY=option_y,
        fontSize=14,
        color=PURPLE
    )
    option_y += 25
    
    pm.draw_text(
        text="enemy color",
        posX=Menu.x + 15,
        posY=option_y,
        fontSize=12,
        color=WHITE
    )
    
    enemy_color_y = option_y
    
    pm.draw_rectangle(
        posX=Menu.x + Menu.width - 80,
        posY=option_y + 2,
        width=60,
        height=15,
        color=Config.enemy_color
    )
    
    if Menu.show and Mouse.pressed and not Mouse.last_pressed and Menu.x + Menu.width - 80 <= Mouse.x <= Menu.x + Menu.width - 20 and option_y + 2 <= Mouse.y <= option_y + 17:
        Menu.color_picker_active = True
        Menu.color_picker_target = "enemy"
        Menu.color_picker_x = Menu.x + 100
        Menu.color_picker_y = option_y + 25
    
    option_y += 25
    
    pm.draw_text(
        text="teammate color",
        posX=Menu.x + 15,
        posY=option_y,
        fontSize=12,
        color=WHITE
    )
    
    teammate_color_y = option_y
    
    pm.draw_rectangle(
        posX=Menu.x + Menu.width - 80,
        posY=option_y + 2,
        width=60,
        height=15,
        color=Config.friend_color
    )
    
    if Menu.show and Mouse.pressed and not Mouse.last_pressed and Menu.x + Menu.width - 80 <= Mouse.x <= Menu.x + Menu.width - 20 and option_y + 2 <= Mouse.y <= option_y + 17:
        Menu.color_picker_active = True
        Menu.color_picker_target = "teammate"
        Menu.color_picker_x = Menu.x + 100
        Menu.color_picker_y = option_y + 25
    
    option_y += 35
    
    pm.draw_text(
        text="legend",
        posX=Menu.x + 15,
        posY=option_y,
        fontSize=14,
        color=PURPLE
    )
    option_y += 25
    
    pm.draw_rectangle(
        posX=Menu.x + 15,
        posY=option_y + 6,
        width=10,
        height=10,
        color=Config.enemy_color
    )
    pm.draw_text(
        text="enemies",
        posX=Menu.x + 35,
        posY=option_y,
        fontSize=12,
        color=WHITE
    )
    option_y += 25
    
    pm.draw_rectangle(
        posX=Menu.x + 15,
        posY=option_y + 6,
        width=10,
        height=10,
        color=Config.friend_color
    )
    pm.draw_text(
        text="teammates",
        posX=Menu.x + 35,
        posY=option_y,
        fontSize=12,
        color=WHITE
    )
    option_y += 35
    
    pm.draw_text(
        text="other settings",
        posX=Menu.x + 15,
        posY=option_y,
        fontSize=14,
        color=PURPLE
    )
    option_y += 25
    
    pm.draw_text(
        text="only render when cs2 focused",
        posX=Menu.x + 15,
        posY=option_y,
        fontSize=12,
        color=WHITE
    )
    draw_toggle(Menu.x + Menu.width - 40, option_y, Config.only_render_when_focused, "only_render_when_focused")
    option_y += 25
    
    app = App.get_instance()
    if app:
        status_text = "status: active" if app.esp.cs2_focused else "status: inactive"
        status_color = GREEN if app.esp.cs2_focused else GRAY
        
        pm.draw_text(
            text=status_text,
            posX=Menu.x + 15,
            posY=option_y,
            fontSize=12,
            color=status_color
        )
        option_y += 35
    
    pm.draw_text(
        text="press insert to toggle menu",
        posX=Menu.x + 15,
        posY=option_y,
        fontSize=11,
        color=pm.fade_color(WHITE, 0.7)
    )
    
    credits_text = "made by ambrosial"
    credits_width = pm.measure_text(text=credits_text, fontSize=11)
    pm.draw_text(
        text=credits_text,
        posX=Menu.x + (Menu.width - credits_width) / 2,
        posY=Menu.y + Menu.height - 15,
        fontSize=11,
        color=pm.fade_color(PURPLE, 0.7)
    )
    
    # update counter
    update_text = "update: 0"
    pm.draw_text(
        text=update_text,
        posX=Menu.x + Menu.width - 60,
        posY=Menu.y + Menu.height - 15,
        fontSize=9,
        color=pm.fade_color(WHITE, 0.5)
    )

    if Menu.color_picker_active:
        draw_color_picker(Menu.color_picker_x, Menu.color_picker_y, Menu.color_picker_target)

def draw_toggle(x, y, state, option_name):
    pm.draw_rectangle_rounded(
        posX=x,
        posY=y,
        width=25,
        height=14,
        roundness=0.5,
        segments=8,
        color=pm.fade_color(PURPLE if state else BLACK, 0.7)
    )
    
    pm.draw_circle(
        centerX=x + (18 if state else 7),
        centerY=y + 7,
        radius=5,
        color=WHITE
    )
    
    if Menu.show and Mouse.pressed and not Mouse.last_pressed and x <= Mouse.x <= x + 25 and y <= Mouse.y <= y + 14:
        if option_name == "enemy_box":
            Config.enemy_box = not Config.enemy_box
        elif option_name == "enemy_health":
            Config.enemy_health = not Config.enemy_health
        elif option_name == "enemy_name":
            Config.enemy_name = not Config.enemy_name
        elif option_name == "enemy_distance":
            Config.enemy_distance = not Config.enemy_distance
        elif option_name == "enemy_skeleton":
            Config.enemy_skeleton = not Config.enemy_skeleton
        elif option_name == "enemy_weapon":
            Config.enemy_weapon = not Config.enemy_weapon
        elif option_name == "enemy_line":
            Config.enemy_line = not Config.enemy_line
        elif option_name == "show_teammates":
            Config.show_teammates = not Config.show_teammates
        elif option_name == "only_render_when_focused":
            Config.only_render_when_focused = not Config.only_render_when_focused

def draw_color_picker(x, y, target):
    pm.draw_rectangle_rounded(
        posX=x,
        posY=y,
        width=180,
        height=80,
        roundness=0.1,
        segments=8,
        color=pm.fade_color(BLACK, 0.95)
    )
    
    title_text = "select color"
    title_width = pm.measure_text(text=title_text, fontSize=12)
    pm.draw_text(
        text=title_text,
        posX=x + (180 - title_width) / 2,
        posY=y + 5,
        fontSize=12,
        color=WHITE
    )
    
    swatch_size = 20
    margin = 5
    colors_per_row = 4
    
    for i, color_option in enumerate(Config.available_colors):
        row = i // colors_per_row
        col = i % colors_per_row
        
        swatch_x = x + margin + (swatch_size + margin) * col
        swatch_y = y + margin + (swatch_size + margin) * row + 15
        
        pm.draw_rectangle(
            posX=swatch_x,
            posY=swatch_y,
            width=swatch_size,
            height=swatch_size,
            color=color_option["color"]
        )
        
        if Menu.show and Mouse.pressed and not Mouse.last_pressed and swatch_x <= Mouse.x <= swatch_x + swatch_size and swatch_y <= Mouse.y <= swatch_y + swatch_size:
            if target == "enemy":
                Config.enemy_color = color_option["color"]
            elif target == "teammate":
                Config.friend_color = color_option["color"]
            
            Menu.color_picker_active = False

def draw_watermark():
    app = App.get_instance()
    if not app:
        return
        
    if not Config.watermark or (Config.only_render_when_focused and not app.esp.cs2_focused and not Menu.show):
        return
    
    current_time = time.strftime("%H:%M:%S", time.localtime())
    watermark_text = f"cs2 simple esp | {current_time}"
    
    if Config.only_render_when_focused:
        focus_status = " [ACTIVE]" if app.esp.cs2_focused else " [INACTIVE]"
        watermark_text += focus_status
    
    text_width = pm.measure_text(text=watermark_text, fontSize=14)
    
    bg_color = BLACK
    accent_color = PURPLE if app.esp.cs2_focused or not Config.only_render_when_focused else GRAY
    text_color = WHITE if app.esp.cs2_focused or not Config.only_render_when_focused else GRAY
    
    pm.draw_rectangle_rounded(
        posX=10,
        posY=10,
        width=text_width + 20,
        height=25,
        roundness=0.5,
        segments=6,
        color=pm.fade_color(bg_color, 0.85)
    )
    
    pm.draw_rectangle_rounded(
        posX=10,
        posY=33,
        width=text_width + 20,
        height=2,
        roundness=0.5,
        segments=6,
        color=accent_color
    )
    
    pm.draw_text(
        text=watermark_text,
        posX=20,
        posY=15,
        fontSize=14,
        color=text_color
    )

class App:
    _instance = None

    def __init__(self):
        if App._instance is not None:
            raise Exception(".")
        App._instance = self
        
        if not pm.process_exists(processName="cs2.exe"):
            ctypes.windll.user32.MessageBoxW(0, "cs2.exe process was not found\n\nplease open the game and try again", "error", 0x10)
            sys.exit(0)
        
        title = ''.join(random.choice(string.ascii_lowercase) for _ in range(10))
        
        pm.overlay_init(target=title, title=title, fps=144, exitKey=0)
        pm.set_fps(pm.get_monitor_refresh_rate())
        
        self.process = pm.open_process("cs2.exe")
        self.module = pm.get_module(self.process, "client.dll")["base"]
        
        print("initializing offsets..")
        self.init_offsets()
        
        self.esp = ESP(self.process, self.module)
        
    def init_offsets(self):
        try:
            global dwEntityList, dwViewMatrix, dwLocalPlayerPawn, dwLocalPlayerController, m_iszPlayerName
            global m_iHealth, m_iTeamNum, m_vOldOrigin, m_pGameSceneNode, m_hPlayerPawn
            global m_ArmorValue, m_pClippingWeapon, m_AttributeManager, m_Item, m_iItemDefinitionIndex, m_pBoneArray
            
            print("fetching offsets..")
            offsets = requests.get("https://raw.githubusercontent.com/a2x/cs2-dumper/main/output/offsets.json").json()
            client_dll = requests.get("https://raw.githubusercontent.com/a2x/cs2-dumper/main/output/client_dll.json").json()
            
            print("processing offsets..")
            dwEntityList = offsets["client.dll"]["dwEntityList"]
            dwViewMatrix = offsets["client.dll"]["dwViewMatrix"]
            dwLocalPlayerPawn = offsets["client.dll"]["dwLocalPlayerPawn"]
            dwLocalPlayerController = offsets["client.dll"]["dwLocalPlayerController"]
            
            m_iszPlayerName = client_dll["client.dll"]["classes"]["CBasePlayerController"]["fields"]["m_iszPlayerName"]
            m_iHealth = client_dll["client.dll"]["classes"]["C_BaseEntity"]["fields"]["m_iHealth"]
            m_iTeamNum = client_dll["client.dll"]["classes"]["C_BaseEntity"]["fields"]["m_iTeamNum"]
            m_vOldOrigin = client_dll["client.dll"]["classes"]["C_BasePlayerPawn"]["fields"]["m_vOldOrigin"]
            m_pGameSceneNode = client_dll["client.dll"]["classes"]["C_BaseEntity"]["fields"]["m_pGameSceneNode"]
            m_hPlayerPawn = client_dll["client.dll"]["classes"]["CCSPlayerController"]["fields"]["m_hPlayerPawn"]
            m_ArmorValue = client_dll["client.dll"]["classes"]["C_CSPlayerPawn"]["fields"]["m_ArmorValue"]
            m_pClippingWeapon = client_dll["client.dll"]["classes"]["C_CSPlayerPawnBase"]["fields"]["m_pClippingWeapon"]
            m_AttributeManager = client_dll["client.dll"]["classes"]["C_EconEntity"]["fields"]["m_AttributeManager"]
            m_Item = client_dll["client.dll"]["classes"]["C_AttributeContainer"]["fields"]["m_Item"]
            m_iItemDefinitionIndex = client_dll["client.dll"]["classes"]["C_EconItemView"]["fields"]["m_iItemDefinitionIndex"]
            m_pBoneArray = client_dll["client.dll"]["classes"]["CSkeletonInstance"]["fields"]["m_modelState"] + 128
            
            print("offsets initialized successfully")
        except Exception as e:
            error_msg = f"failed to get offsets: {str(e)}\nplease check your internet connection"
            ctypes.windll.user32.MessageBoxW(0, error_msg, "error", 0x10)
            sys.exit(0)
    
    def run(self):
        print("running esp - press insert to toggle menu")
        
        while pm.overlay_loop():
            try:
                pm.begin_drawing()
                
                update_mouse()
                
                draw_watermark()
                
                self.esp.update()
                
                toggle_menu()
                drag_menu()
                draw_menu()
                
                pm.end_drawing()
            except Exception as e:
                print(f"error in main loop: {str(e)}")
                continue
        
        print("exiting..")

    @classmethod
    def get_instance(cls):
        return cls._instance

if __name__ == "__main__":
    try:
        app = App()
        app.run()
    except Exception as e:
        error_msg = f"an error occurred: {str(e)}"
        ctypes.windll.user32.MessageBoxW(0, error_msg, "error", 0x10) 