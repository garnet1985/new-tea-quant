#!/bin/bash
# PostgreSQL 快速配置脚本
# 用于 stocks-py 项目迁移

# PostgreSQL 安装路径
PG_BIN="/Library/PostgreSQL/18/bin"
PG_USER="postgres"
DB_NAME="stocks_py"
DB_USER="stocks_user"

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== PostgreSQL 配置脚本 ===${NC}\n"

# 检查 PostgreSQL 是否安装
if [ ! -f "$PG_BIN/psql" ]; then
    echo -e "${YELLOW}错误: 找不到 PostgreSQL，请检查安装路径${NC}"
    exit 1
fi

echo "✅ PostgreSQL 已找到: $PG_BIN/psql"

# 添加到 PATH（当前会话）
export PATH="$PG_BIN:$PATH"

# 提示输入 postgres 密码
echo -e "\n${YELLOW}请输入 postgres 用户密码:${NC}"
read -s PGPASSWORD
export PGPASSWORD

# 测试连接
echo -e "\n${GREEN}测试连接...${NC}"
if $PG_BIN/psql -U $PG_USER -c "SELECT version();" > /dev/null 2>&1; then
    echo "✅ 连接成功"
else
    echo -e "${YELLOW}❌ 连接失败，请检查密码${NC}"
    exit 1
fi

# 创建数据库
echo -e "\n${GREEN}创建数据库: $DB_NAME${NC}"
if $PG_BIN/psql -U $PG_USER -lqt | cut -d \| -f 1 | grep -qw $DB_NAME; then
    echo "⚠️  数据库 $DB_NAME 已存在，跳过创建"
else
    $PG_BIN/createdb -U $PG_USER $DB_NAME
    if [ $? -eq 0 ]; then
        echo "✅ 数据库创建成功"
    else
        echo -e "${YELLOW}❌ 数据库创建失败${NC}"
        exit 1
    fi
fi

# 创建用户
echo -e "\n${GREEN}创建用户: $DB_USER${NC}"
echo -e "${YELLOW}请输入新用户密码:${NC}"
read -s USER_PASSWORD

if $PG_BIN/psql -U $PG_USER -d $DB_NAME -tc "SELECT 1 FROM pg_user WHERE usename = '$DB_USER'" | grep -q 1; then
    echo "⚠️  用户 $DB_USER 已存在，更新密码..."
    $PG_BIN/psql -U $PG_USER -d $DB_NAME -c "ALTER USER $DB_USER WITH PASSWORD '$USER_PASSWORD';"
else
    $PG_BIN/psql -U $PG_USER -d $DB_NAME -c "CREATE USER $DB_USER WITH PASSWORD '$USER_PASSWORD';"
fi

if [ $? -eq 0 ]; then
    echo "✅ 用户创建/更新成功"
else
    echo -e "${YELLOW}❌ 用户创建失败${NC}"
    exit 1
fi

# 授予权限
echo -e "\n${GREEN}授予权限...${NC}"
$PG_BIN/psql -U $PG_USER -d $DB_NAME -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"
$PG_BIN/psql -U $PG_USER -d $DB_NAME -c "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO $DB_USER;"
$PG_BIN/psql -U $PG_USER -d $DB_NAME -c "GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO $DB_USER;"
$PG_BIN/psql -U $PG_USER -d $DB_NAME -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO $DB_USER;"
$PG_BIN/psql -U $PG_USER -d $DB_NAME -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO $DB_USER;"

if [ $? -eq 0 ]; then
    echo "✅ 权限授予成功"
else
    echo -e "${YELLOW}❌ 权限授予失败${NC}"
    exit 1
fi

# 测试新用户连接
echo -e "\n${GREEN}测试新用户连接...${NC}"
export PGPASSWORD=$USER_PASSWORD
if $PG_BIN/psql -U $DB_USER -d $DB_NAME -c "SELECT current_user, current_database();" > /dev/null 2>&1; then
    echo "✅ 新用户连接成功"
else
    echo -e "${YELLOW}❌ 新用户连接失败${NC}"
    exit 1
fi

# 显示连接信息
echo -e "\n${GREEN}=== 配置完成 ===${NC}\n"
echo "数据库名称: $DB_NAME"
echo "用户名: $DB_USER"
echo "主机: localhost"
echo "端口: 5432"
echo ""
echo -e "${GREEN}连接命令:${NC}"
echo "export PATH=\"$PG_BIN:\$PATH\""
echo "export PGPASSWORD='$USER_PASSWORD'"
echo "psql -U $DB_USER -d $DB_NAME -h localhost"
echo ""
echo -e "${GREEN}或者使用完整路径:${NC}"
echo "$PG_BIN/psql -U $DB_USER -d $DB_NAME -h localhost"
echo ""
