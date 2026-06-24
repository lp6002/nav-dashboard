@echo off
cd /d "C:\Users\lp263\工作空间\导航页"
echo 🚀 启动本地服务...
echo.
echo 📊 游戏投放管理(实时同步): http://127.0.0.1:8765/games_sync.html
echo 🤖 AI群聊:               http://127.0.0.1:8765/ai_group.html
echo.
python proxy_server.py
pause
