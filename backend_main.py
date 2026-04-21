import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ==========================================
# 1. 导入数据库地基
# ==========================================
from db.database import engine
from db import models

# ==========================================
# 2. 导入你的四大核心业务路由
# ==========================================
# (注意：如果你的模块名有细微差别，请以你实际的文件名为准)
from routers import auth, student, teacher, ai

# ==========================================
# 3. 物理建表 (引擎启动前的基建)
# ==========================================
# 每次启动时，系统会自动检查表结构，缺什么表就建什么表
models.Base.metadata.create_all(bind=engine)

# ==========================================
# 4. 实例化 FastAPI 主引擎
# ==========================================
app = FastAPI(
    title="WUT 经管 AI 科研平台",
    description="武汉理工大学经济学院 - 智能教务与加分审批系统引擎",
    version="3.5.0"
)

# ==========================================
# 5. 配置跨域护盾 (CORS) - 极其关键！
# ==========================================
# 没有这段代码，跑在 5173 端口的 Vue 绝对无法访问跑在 8000 端口的 FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发测试阶段允许所有来源，上线时可改为 ["http://localhost:5173"]
    allow_credentials=True,
    allow_methods=["*"],  # 允许 GET, POST, PUT, DELETE 等所有动作
    allow_headers=["*"],  # 允许携带任意 Token 和 Headers
)

# ==========================================
# 6. 注册四大业务模块 (插上翅膀)
# ==========================================
app.include_router(auth.router)     # 🛡️ 安保局：白名单校验、注册、密码/验证码登录
app.include_router(student.router)  # 🎓 学生端：提交申请、星盘看板拉取、AI 智能聊天
app.include_router(teacher.router)  # 👨‍🏫 教师端：名单导入导出、全量审批大屏
app.include_router(ai.router)       # 🧠 AI 视觉舱：负责接收图片并呼叫 engine.py 提取 JSON

# ==========================================
# 7. 系统健康检查探针
# ==========================================
# 当你直接访问 http://127.0.0.1:8000/ 时，就是它在回应你
@app.get("/", tags=["系统探针"])
async def root():
    return {
        "status": "success",
        "message": "🚀 WUT Economy AI Engine is running perfectly!",
        "version": "3.5.0"
    }

# ==========================================
# 8. 本地热启动入口
# ==========================================
if __name__ == "__main__":
    print("⚡ 正在启动后端核心引擎...")
    print("👉 Swagger API 文档地址: http://127.0.0.1:8000/docs")
    # reload=True 意味着你修改任何 python 文件，它都会自动热重启，无需手动关停
    uvicorn.run("backend_main:app", host="127.0.0.1", port=8000, reload=True)