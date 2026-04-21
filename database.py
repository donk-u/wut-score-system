import sqlite3
import os

# 1. 确定数据库文件的位置
DB_PATH = 'data/wut_system.db'

def init_db():
    """就像盖房子前先打地基，这个函数负责创建表结构"""
    # 如果 data 文件夹不存在，先建一个
    if not os.path.exists('data'):
        os.makedirs('data')
        
    # 连接数据库（如果不存在会自动创建）
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 创建学生表：存那 10 个人的基本信息
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            student_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            major TEXT DEFAULT '经济学院'
        )
    ''')

    # 创建申请记录表：存学生上传的证书和 AI 计算的结果
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT,
            contest_name TEXT,     -- 比赛名字
            award_level TEXT,      -- 获奖等级 (如 A1-省一)
            user_rank INTEGER,     -- 学生自填的排名
            ai_score REAL,         -- 系统算出的加分
            status TEXT DEFAULT '待审核', -- 状态：待审核/已通过/已驳回
            image_path TEXT,       -- 证书图片存哪了
            FOREIGN KEY (student_id) REFERENCES students (student_id)
        )
    ''')

    conn.commit()
    conn.close()
    print("✅ 数据库地基已打好！")

def seed_students():
    """给系统先塞入 10 个学生名单，方便我们测试登录"""
    students_list = [
        ('2024001', '张三', '智能经济'),
        ('2024002', '李四', '智能经济'),
        ('2024003', '王五', '金融学'),
        # 你可以继续往后加到 10 个...
    ]
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # OR IGNORE 是为了防止重复运行代码导致报错
    cursor.executemany('INSERT OR IGNORE INTO students VALUES (?, ?, ?)', students_list)
    conn.commit()
    conn.close()
    print(f"✅ 已成功导入 {len(students_list)} 名初始学生。")

# 只要运行这个 database.py，就会自动执行初始化
if __name__ == "__main__":
    init_db()
    seed_students()
import sqlite3

conn = sqlite3.connect('data/wut_system.db')
cursor = conn.cursor()

# 给 records 表增加一个 comment（评语）字段
try:
    cursor.execute("ALTER TABLE records ADD COLUMN comment TEXT")
    conn.commit()
    print("✅ 数据库升级成功：已增加评语字段！")
except:
    print("⚠️ 评语字段可能已经存在，无需重复增加。")

conn.close()