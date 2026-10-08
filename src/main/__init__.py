# -*- coding: utf-8 -*-
"""AIM 2627 Python Coursework —— 哨兵 Sentry 控制模块（学生骨架）。

你的全部作业都在本文件里：按题面（题面.pdf）各题的规范补全每个标有 TODO 的函数。
- 骨架已提供：Facing / SentryState 枚举、SentryGrid 的构造与只读属性、
  渲染函数 render_frame（demo 用，不进测试）。
- 你要实现：Q1-Q6 与 Bonus 的全部 TODO，以及 SentryGrid 的
  四个方法（current_pos 的 setter、move_forward、turn_left、turn_right）。
- 未实现的函数 raise NotImplementedError：可见测试会自动 skip，
  CI 一开始就是绿的；实现一个，对应测试亮一个。
- `python main.py`（或 PYTHONPATH=src python -m main）可看 ASCII 演示。
"""
import json
from collections import deque
from enum import Enum


# ---------------------------------------------------------------------------
# 仿真世界基础（已提供，勿改）
# ---------------------------------------------------------------------------
class Facing(Enum):
    """朝向枚举。世界坐标 (x, y)：x 向右增长，y 向上增长（数学系）。"""

    UP = (0, 1)
    DOWN = (0, -1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)

    @property
    def delta(self):
        """该朝向的单位位移向量 (dx, dy)。"""
        return self.value[0], self.value[1]


# ---------------------------------------------------------------------------
# Q1 机器人自检（题面 Q1·自检状态计算与报告生成）
# ---------------------------------------------------------------------------
def hp_ratio(hp, max_hp):
    """TODO(Q1)：血量百分比，返回 0-100 的 int；计算与边界规则见题面 Q1 规范。"""
    if max_hp <= 0:
        return 0
    return max(0, min(100, int(hp * 100 / max_hp)))


def status_report(name, robot_type, hp, max_hp, battery):
    """TODO(Q1)：一行自检报告字符串；档位判定与逐字符格式见题面 Q1 规范。"""
    hp_pct = hp_ratio(hp, max_hp)
    bat_pct = max(0, min(100, int(battery)))

    if bat_pct >= 50:
        level = "OK"
    elif bat_pct >= 20:
        level = "WARNING"
    else:
        level = "LOW"

    return f"{name:<10}|{robot_type:^10}|HP {hp_pct:>3}%|BAT {bat_pct:>3}%|{level}"


# ---------------------------------------------------------------------------
# Q2 战斗日志分析（题面 Q2·多源日志解析与统计）
# ---------------------------------------------------------------------------
def analyze_damage_log(lines):
    """TODO(Q2)：解析混合格式伤害日志，返回固定契约的统计 dict；
    行格式、去重与统计口径见题面 Q2 规范。"""
    armor_codes = {"F": "front", "L": "left", "R": "right"}
    armor_totals = {"front": 0, "left": 0, "right": 0}
    total = 0
    record_count = 0
    seen_ids = set()

    for line in lines:
        if not isinstance(line, str):
            continue
        text = line.strip()
        if not text or text.startswith("#"):
            continue

        if text.startswith("{"):
            try:
                record = json.loads(text)
            except (TypeError, ValueError):
                continue
            if not isinstance(record, dict):
                continue

            armor = record.get("armor")
            damage = record.get("damage")
            if (not isinstance(armor, str) or armor not in armor_totals
                    or isinstance(damage, bool)
                    or not isinstance(damage, int) or damage < 0):
                continue

            if "id" in record:
                record_id = json.dumps(record["id"], sort_keys=True)
                if record_id in seen_ids:
                    continue
                seen_ids.add(record_id)

            damage_by_armor = {armor: damage}
        else:
            damage_by_armor = {}
            parts = text.split(",")
            valid_line = bool(parts)
            for part in parts:
                code, separator, value = part.partition(":")
                code = code.strip().upper()
                value = value.strip()
                if (not separator or code not in armor_codes
                        or not value or not value.isdecimal()):
                    valid_line = False
                    break
                armor = armor_codes[code]
                if armor in damage_by_armor:
                    valid_line = False
                    break
                damage_by_armor[armor] = int(value)
            if not valid_line:
                continue

        for armor, damage in damage_by_armor.items():
            armor_totals[armor] += damage
            total += damage
        record_count += 1

    most_hit = None
    if total:
        most_hit = max(armor_totals, key=armor_totals.get)

    return {
        "total": total,
        "by_armor": armor_totals,
        "most_hit": most_hit,
        "avg": total / record_count if record_count else 0.0,
    }


# ---------------------------------------------------------------------------
# Q3 SentryGrid（题面 Q3·载体物理规则）
# ---------------------------------------------------------------------------
class SentryGrid:
    """哨兵仿真载体（构造与只读属性已提供；四个 TODO 方法由你实现）。"""

    def __init__(self, width, height, obstacles, enemy_pos,
                 start_pos=(0, 0), facing=Facing.UP, fuel=100):
        self._width = int(width)
        self._height = int(height)
        if self._width <= 0 or self._height <= 0:
            raise ValueError("地图尺寸必须为正")
        # 障碍坐标存入 set，查询 O(1)——已有实现，勿改。
        self._obstacles = set()
        for ob in obstacles:
            x, y = ob
            self._obstacles.add((int(x), int(y)))
        if not isinstance(enemy_pos, (tuple, list)) or len(enemy_pos) != 2:
            raise TypeError("enemy_pos 需要长度为 2 的 tuple/list")
        self._enemy_pos = self._clamp_cell(enemy_pos)
        if self._enemy_pos in self._obstacles:
            raise ValueError("enemy_pos 不能位于障碍物上")
        if not isinstance(facing, Facing):
            facing = Facing.UP
        self._facing = facing
        self._fuel = int(fuel)
        self._collision_count = 0
        self._pos = self._clamp_cell(start_pos)
        if self._pos in self._obstacles:
            raise ValueError("start_pos 不能位于障碍物上")

    def _clamp_cell(self, cell):
        """已提供：元素转 int 并夹回地图范围（供 __init__ 使用）。"""
        x = int(cell[0])
        y = int(cell[1])
        x = max(0, min(self._width - 1, x))
        y = max(0, min(self._height - 1, y))
        return (x, y)

    # -- 只读属性（已提供，勿改） ------------------------------------------
    @property
    def width(self):
        return self._width

    @property
    def height(self):
        return self._height

    @property
    def enemy_pos(self):
        return self._enemy_pos

    @property
    def facing(self):
        return self._facing

    @property
    def fuel(self):
        return self._fuel

    @property
    def collision_count(self):
        return self._collision_count

    @property
    def obstacles(self):
        """障碍集合的只读视图（内部 set 引用，不要修改它）。"""
        return self._obstacles

    @property
    def found_enemy(self):
        return self._pos == self._enemy_pos

    def is_blocked(self, x, y):
        """已提供：坐标是否为障碍或越界（O(1)）。"""
        return ((x, y) in self._obstacles
                or not (0 <= x < self._width and 0 <= y < self._height))

    # -- 你要实现的部分 ------------------------------------------------------
    @property
    def current_pos(self):
        """当前位置 (x, y) 的 tuple。"""
        return self._pos

    @current_pos.setter
    def current_pos(self, value):
        """TODO(Q3)：位置 setter；三重输入校验见题面 Q3 规范第 1 条。"""
        if not isinstance(value, (tuple, list)) or len(value) != 2:
            raise TypeError("current_pos 需要长度为 2 的 tuple/list")
        self._pos = self._clamp_cell(value)

    def move_forward(self):
        """TODO(Q3)：朝当前 facing 前进一格，返回执行后的位置；
        碰撞、耗电与断电语义见题面 Q3 规范。"""
        if self._fuel <= 0:
            return self._pos

        self._fuel -= 1
        dx, dy = self._facing.delta
        next_x = self._pos[0] + dx
        next_y = self._pos[1] + dy
        if self.is_blocked(next_x, next_y):
            self._collision_count += 1
            return self._pos

        self._pos = (next_x, next_y)
        return self._pos

    def turn_left(self):
        """TODO(Q3)：原地左转 90°，返回新的 Facing（不耗电）。"""
        self._facing = {
            Facing.UP: Facing.LEFT,
            Facing.LEFT: Facing.DOWN,
            Facing.DOWN: Facing.RIGHT,
            Facing.RIGHT: Facing.UP,
        }[self._facing]
        return self._facing

    def turn_right(self):
        """TODO(Q3)：原地右转 90°，返回新的 Facing（不耗电）。"""
        self._facing = {
            Facing.UP: Facing.RIGHT,
            Facing.RIGHT: Facing.DOWN,
            Facing.DOWN: Facing.LEFT,
            Facing.LEFT: Facing.UP,
        }[self._facing]
        return self._facing


# ---------------------------------------------------------------------------
# Q4 贪心导航（题面 Q4·单步贪心导航策略）
# ---------------------------------------------------------------------------
def next_step_toward(pos, target, obstacles, current_facing=Facing.UP):
    """TODO(Q4)：返回下一步应朝向的 Facing；
    候选判定、优先级与回退规则见题面 Q4 规范。"""
    dx = target[0] - pos[0]
    dy = target[1] - pos[1]

    horizontal = None
    if dx > 0:
        horizontal = (Facing.RIGHT, (pos[0] + 1, pos[1]))
    elif dx < 0:
        horizontal = (Facing.LEFT, (pos[0] - 1, pos[1]))

    vertical = None
    if dy > 0:
        vertical = (Facing.UP, (pos[0], pos[1] + 1))
    elif dy < 0:
        vertical = (Facing.DOWN, (pos[0], pos[1] - 1))

    candidates = [horizontal, vertical] if abs(dx) > abs(dy) else [
        vertical, horizontal]
    for candidate in candidates:
        if candidate is not None and candidate[1] not in obstacles:
            return candidate[0]

    return current_facing


# ---------------------------------------------------------------------------
# Q5 哨兵决策机（题面 Q5·裁判系统决策规则表）
# ---------------------------------------------------------------------------
class SentryState(Enum):
    """哨兵状态机（已提供，勿改）。"""

    PATROL = "PATROL"
    SUSPECT = "SUSPECT"
    ENGAGE = "ENGAGE"
    RETREAT = "RETREAT"
    RETURN = "RETURN"


def decide(sensor, state, hp, heat):
    """TODO(Q5)：纯函数决策，返回 (action: str, new_state: SentryState)；
    sensor 字段契约、R1-R7 规则表与非法输入处理见题面 Q5 规范。"""
    required_fields = {"enemy_frames", "enemy_dist", "robot_type", "max_hp"}
    if not isinstance(sensor, dict) or not required_fields.issubset(sensor):
        raise ValueError("sensor 缺少必需字段")
    if not isinstance(state, SentryState):
        raise ValueError("state 必须是 SentryState 成员")

    enemy_frames = sensor["enemy_frames"]
    if not isinstance(enemy_frames, (tuple, list)):
        enemy_frames = (False,)
    if not 1 <= len(enemy_frames) <= 6:
        raise ValueError("enemy_frames 长度必须为 1 到 6")
    enemy_frames = tuple(bool(frame) for frame in enemy_frames)

    enemy_dist = sensor["enemy_dist"]
    if (isinstance(enemy_dist, bool) or not isinstance(enemy_dist, int)
            or enemy_dist < 0):
        enemy_dist = None

    robot_type = sensor["robot_type"]
    if robot_type not in ("INFANTRY", "HERO"):
        robot_type = "INFANTRY"

    max_hp = sensor["max_hp"]
    try:
        if isinstance(hp, bool) or isinstance(max_hp, bool) or max_hp <= 0:
            raise ValueError
        hp_pct = int(hp * 100 / max_hp)
    except (TypeError, ValueError, OverflowError, ZeroDivisionError):
        hp_pct = 0
    hp_pct = max(0, min(100, hp_pct))

    visible = enemy_frames[-1]

    def engage_action():
        if enemy_dist is not None and enemy_dist <= 3:
            return "SHOOT", SentryState.ENGAGE
        if robot_type == "HERO":
            return "MOVE_RIGHT", SentryState.ENGAGE
        return "MOVE_LEFT", SentryState.ENGAGE

    if hp_pct <= 30:
        return "RETREAT", SentryState.RETREAT

    if state is SentryState.RETREAT:
        return "RETURN", SentryState.RETURN

    if state is SentryState.RETURN:
        return "MOVE_BASE", SentryState.PATROL

    if state is SentryState.ENGAGE:
        if visible:
            return engage_action()
        if len(enemy_frames) >= 2 and not enemy_frames[-2]:
            return "SCAN", SentryState.SUSPECT
        return "HOLD_FIRE", SentryState.ENGAGE

    if visible:
        if len(enemy_frames) >= 2 and enemy_frames[-2]:
            return engage_action()
        return "SCAN", SentryState.SUSPECT

    if state is SentryState.PATROL:
        return "PATROL_MOVE", SentryState.PATROL
    return "SCAN", SentryState.SUSPECT


# ---------------------------------------------------------------------------
# Q6 巡逻任务（题面 Q6·巡逻契约与验收阈值）
# ---------------------------------------------------------------------------
def run_patrol(grid, max_steps=500):
    """TODO(Q6)：sense → decide → act 主循环；
    循环结构、终止条件、脱困自由度与统计返回契约见题面 Q6 规范。"""
    clockwise = (Facing.UP, Facing.RIGHT, Facing.DOWN, Facing.LEFT)
    turn_index = {facing: index for index, facing in enumerate(clockwise)}
    left_of = {
        Facing.UP: Facing.LEFT,
        Facing.LEFT: Facing.DOWN,
        Facing.DOWN: Facing.RIGHT,
        Facing.RIGHT: Facing.UP,
    }
    right_of = {right: left for left, right in left_of.items()}

    def manhattan(pos):
        return abs(pos[0] - grid.enemy_pos[0]) + abs(pos[1] - grid.enemy_pos[1])

    def has_greedy_candidate(pos):
        distance = manhattan(pos)
        for facing in Facing:
            dx, dy = facing.delta
            next_pos = (pos[0] + dx, pos[1] + dy)
            if (not grid.is_blocked(*next_pos)
                    and manhattan(next_pos) < distance):
                return True
        return False

    initial_collisions = grid.collision_count
    visited = {grid.current_pos}
    steps = 0
    wall_following = False
    hand = "L"
    wall_steps = 0
    wall_entry_distance = 0
    wall_limit = grid.width + grid.height

    while (steps < max_steps and grid.fuel > 0
           and not grid.found_enemy):
        pos = grid.current_pos
        if not wall_following and not has_greedy_candidate(pos):
            wall_following = True
            hand = "L"
            wall_steps = 0
            wall_entry_distance = manhattan(pos)

        if wall_following:
            side = left_of[grid.facing] if hand == "L" else right_of[grid.facing]
            opposite = right_of[grid.facing] if hand == "L" else left_of[grid.facing]

            def next_cell(facing):
                dx, dy = facing.delta
                return pos[0] + dx, pos[1] + dy

            if not grid.is_blocked(*next_cell(side)):
                grid.turn_left() if hand == "L" else grid.turn_right()
            elif grid.is_blocked(*next_cell(grid.facing)):
                if not grid.is_blocked(*next_cell(opposite)):
                    grid.turn_right() if hand == "L" else grid.turn_left()
                else:
                    grid.turn_right()
                    grid.turn_right()
        else:
            direction = next_step_toward(
                pos, grid.enemy_pos, grid.obstacles, grid.facing)
            turns = (turn_index[direction] - turn_index[grid.facing]) % 4
            if turns == 3:
                grid.turn_left()
            else:
                for _ in range(turns):
                    grid.turn_right()

        grid.move_forward()
        steps += 1
        visited.add(grid.current_pos)

        if wall_following:
            wall_steps += 1
            if wall_steps > wall_limit and hand == "L":
                hand = "R"
                wall_steps = 0
            elif wall_steps > 2 * wall_limit:
                wall_following = False
            elif (has_greedy_candidate(grid.current_pos)
                  and manhattan(grid.current_pos) <= wall_entry_distance):
                wall_following = False

    found_enemy = grid.found_enemy
    return {
        "steps": steps,
        "collisions": grid.collision_count - initial_collisions,
        "visited_count": len(visited),
        "found_enemy": found_enemy,
        "success": found_enemy,
    }


def report_to_json(stats):
    """TODO(Q6)：把 stats 序列化为确定性的 JSON 字符串，见题面 Q6 规范。"""
    return json.dumps(stats, sort_keys=True, separators=(",", ":"))


# ---------------------------------------------------------------------------
# Bonus：BFS 全局最短路（题面 Bonus·BFS 语义与排行榜）
# ---------------------------------------------------------------------------
def bfs_path_length(start, target, obstacles):
    """TODO(Bonus)：BFS 全局最短路步数；返回语义与边界职责见题面 Bonus 规范。"""
    if start == target:
        return 0

    obstacles = set(obstacles)
    if start in obstacles or target in obstacles:
        return -1

    queue = deque([(start, 0)])
    visited = {start}
    while queue:
        (x, y), distance = queue.popleft()
        for neighbor in ((x + 1, y), (x - 1, y),
                         (x, y + 1), (x, y - 1)):
            if neighbor in obstacles or neighbor in visited:
                continue
            if neighbor == target:
                return distance + 1
            visited.add(neighbor)
            queue.append((neighbor, distance + 1))

    return -1


# ---------------------------------------------------------------------------
# 渲染（已提供，demo 专用，不进测试）
# ---------------------------------------------------------------------------
def render_frame(grid, trail=()):
    """ASCII 渲染一帧战场；trail 为走过的格子集合。返回 list[str]。"""
    trail = set(trail)
    rows = []
    for y in range(grid.height - 1, -1, -1):
        row = []
        for x in range(grid.width):
            if (x, y) == grid.current_pos:
                row.append("◉")
            elif (x, y) == grid.enemy_pos:
                row.append("▲")
            elif (x, y) in grid.obstacles:
                row.append("█")
            elif (x, y) in trail:
                row.append("·")
            else:
                row.append(".")
        rows.append("".join(row))
    return rows
