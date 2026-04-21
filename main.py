import os
import sys
import time
import subprocess

def start_system():
    print("="*60)
    print("🎓 欢迎使用 武汉理工大学经济学院 - 科研能力分析系统 (SaaS微服务版)")
    print("="*60)
    print("🚀 正在为您唤醒双子星服务器架构...\n")
    
    # 记录前后端的进程，方便最后安全关闭
    processes = []

    try:
        # ==========================================
        # 1. 点火：后端数据核心 (FastAPI)
        # ==========================================
        print("⏳ [1/2] 正在点火后端数据引擎 (FastAPI)...")
        # 相当于在终端输入: python -m uvicorn backend_main:app --reload --port 8000
        backend_cmd = [sys.executable, "-m", "uvicorn", "backend_main:app", "--reload", "--port", "8000"]
        backend_process = subprocess.Popen(backend_cmd)
        processes.append(backend_process)
        
        # 给后端 2 秒钟的时间启动和连通数据库
        time.sleep(2)
        print("✅ 后端核心已上线！[端口: 8000]\n")

        # ==========================================
        # 2. 点火：前端交互橱窗 (Streamlit)
        # ==========================================
        print("⏳ [2/2] 正在加载前端交互界面 (Streamlit)...")
        # 相当于在终端输入: python -m streamlit run frontend_app.py --server.port 8501
        frontend_cmd = [sys.executable, "-m", "streamlit", "run", "frontend_app.py", "--server.port", "8501"]
        frontend_process = subprocess.Popen(frontend_cmd)
        processes.append(frontend_process)
        
        print("✅ 前端界面已上线！[端口: 8501]\n")
        
        print("="*60)
        print("🌐 系统全线贯通！浏览器即将自动打开，请稍候...")
        print("💡 提示：在当前窗口按 【Ctrl+C】 可以同时安全关闭前后端。\n")

        # 阻塞主进程，让它一直盯着这两个子进程
        backend_process.wait()
        frontend_process.wait()

    except KeyboardInterrupt:
        print("\n⚠️ 接收到中断信号！正在执行安全降落程序...")
        # 当你按下 Ctrl+C 时，优雅地关闭前后端进程
        for p in processes:
            p.terminate()
            p.wait()
        print("👋 所有服务已安全离线。感谢使用！")
        sys.exit(0)

if __name__ == "__main__":
    start_system()