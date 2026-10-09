
def status_report(name, robot_type, hp, max_hp, battery):
    """TODO (Q1): 一行自检报告字符串；档位判定与逐字符格式见题面 Q1 规范。"""
    hp_pct = hp_ratio(hp, max_hp)

    # 题目没有给具体电量阈值，此处使用 50 和 20 作为分界线，请根据测试结果调整
    bat_pct = max(0, min(100, int(battery)))  # 同样限制 0-100

    if bat_pct >= 50:
        level = "OK"
    elif bat_pct >= 20:
        level = "WARNING"
    else:
        level = "LOW"

    # 严格按照题面给出的模板格式化字符串
    # {name:<10} 左对齐占10位
    # {robot_type:^10} 居中占10位
    # {hp_pct:>3} 右对齐占3位
    return f"{name:<10}|{robot_type:^10}|HP {hp_pct:>3}%|BAT {bat_pct:>3}%|{level}"
