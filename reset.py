import sqlite3

def hard_reset_database():
    conn = sqlite3.connect('data/wut_system.db')
    cursor = conn.cursor()
    
    # 1. 清空所有记录
    cursor.execute("DELETE FROM records")
    
    # 2. 重置自增 ID 计数器（让下一个变成 1）
    cursor.execute("UPDATE sqlite_sequence SET seq = 0 WHERE name = 'records'")
    
    conn.commit()
    conn.close()
    print("✅ 数据库已彻底清空，记录号已完美重置为 0，下一次提交将从 1 开始！")

hard_reset_database()