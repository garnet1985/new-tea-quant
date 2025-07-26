# Tushare Authentication

## 设置Token

1. 复制 `token.example.txt` 为 `token.txt`：
   ```bash
   cp token.example.txt token.txt
   ```

2. 编辑 `token.txt` 文件，将你的Tushare token替换 `your_tushare_token_here`

3. 确保 `token.txt` 文件被 `.gitignore` 忽略，不会被提交到版本控制

## 获取Tushare Token

1. 访问 [Tushare官网](https://tushare.pro/)
2. 注册并登录账户
3. 在个人中心获取你的token

## 安全注意事项

- 永远不要将 `token.txt` 文件提交到git仓库
- 定期更换token以确保安全
- 如果token泄露，立即在Tushare官网重新生成 