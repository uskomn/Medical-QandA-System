# Medical-QandA-System
# 部署流程
1. xshell连接linux服务器
2. 安装基本环境
# 更新系统
sudo apt update && sudo apt upgrade -y
# 安装 Git
sudo apt install -y git

# 安装 Python3 与 pip
sudo apt install -y python3 python3-venv python3-pip

# 安装 Node.js 和 npm
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
sudo apt install -y nodejs

# 安装 Nginx
sudo apt install -y nginx
sudo systemctl enable nginx
sudo systemctl start nginx
sudo systemctl status nginx
3. 使用git拉取项目
# 创建项目存放目录
sudo mkdir -p /root/MedicalSystem
sudo chown -R $USER:$USER /root/MedicalSystem

cd /root/MedicalSystem

# 使用 Git 拉取项目
git clone 仓库地址
# 假设项目名为 Medical-QandA-System
cd Medical-QandA-System
4. 后端部署
# 创建虚拟环境
cd backend
python3 -m venv venv
source venv/bin/activate
# 安装依赖
pip install -r requirements.txt
# 使用 Gunicorn 启动
backend/venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 'backend.app:create_app()' -D

# 查看进程
ps aux | grep gunicorn
# 砍掉进程
pkill gunicorn
5. 前端部署
# 安装依赖并打包
cd ../frontend
npm install
npm run build
# 拷贝到 Nginx 可访问目录并设置权限
sudo mkdir -p /var/www/medical-frontend
sudo cp -r dist/* /var/www/medical-frontend/
sudo chown -R www-data:www-data /var/www/medical-frontend
sudo chmod -R 755 /var/www/medical-frontend
# 配置 Nginx
sudo nano /etc/nginx/sites-available/default
server {
    listen 80;
    server_name 124.221.149.106;

    # 前端静态文件目录
    root /var/www/your_project/frontend/dist;
    index index.html;

    # 反向代理 Flask 后端
    location /api/ {
        proxy_pass http://127.0.0.1:5000/; 
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 前端 history 模式下解决刷新 404
    location / {
        try_files $uri $uri/ /index.html;
    }
}

ctrl o保存
回车确定
ctrl x推出
# 测试并重启
sudo nginx -t
sudo systemctl restart nginx
# 查看nginx配置
cat /etc/nginx/sites-available/default
6. 测试
# 前端
http://服务器公网ip/
# 后端接口测试
curl http://127.0.0.1:5000/chat/answer_questions
curl http://127.0.0.1:5000/knowledge_graph/test_connection
