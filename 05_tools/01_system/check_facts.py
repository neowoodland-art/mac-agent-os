import sqlite3
import sys

def check_facts_db():
    db_path = "04_memory/long_term/facts.db"
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查表结构
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print("数据库中的表:", tables)
        
        # 检查facts表结构
        if ('facts',) in tables:
            cursor.execute("PRAGMA table_info(facts)")
            columns = cursor.fetchall()
            print("\nfacts表结构:")
            for col in columns:
                print(f"  {col[1]}: {col[2]}")
            
            # 统计条目数
            cursor.execute("SELECT COUNT(*) FROM facts")
            count = cursor.fetchone()[0]
            print(f"\nL2 事实库条目数: {count}")
            
            # 查看最新5条
            cursor.execute("SELECT id, subject, predicate, object, confidence, date_created FROM facts ORDER BY id DESC LIMIT 5")
            print("\n最新5条事实:")
            for row in cursor.fetchall():
                print(f"  ID: {row[0]}, 主题: {row[1]}, 谓词: {row[2]}, 置信度: {row[4]}, 日期: {row[5]}")
                print(f"  内容: {row[3][:100]}...")
                print()
        
        conn.close()
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_facts_db()