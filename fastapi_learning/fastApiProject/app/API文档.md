# FastAPI 学习项目 API 文档

## 基本信息
- 基础地址：`http://127.0.0.1:8080`
- Swagger UI：`http://127.0.0.1:8080/docs`
- 认证方式：`Authorization: Bearer <access_token>`
- 数据格式：默认 JSON，登录和上传使用表单/文件

## 接口总览

| 方法 | 路径 | 说明 | 是否需要认证 |
|------|------|------|--------------|
| GET | `/` | 首页 | 否 |
| GET | `/hello/{name}` | 问候接口 | 否 |
| POST | `/auth/login` | 登录并获取 JWT | 否 |
| POST | `/users/register` | 用户注册 | 否 |
| GET | `/users` | 用户列表 | 否 |
| GET | `/users/me` | 当前登录用户 | 是 |
| GET | `/users/{user_id}` | 按 ID 查询用户 | 否 |
| GET | `/news` | 查询参数示例 | 否 |
| GET | `/items` | 商品分页列表 | 否 |
| POST | `/items` | 创建商品（归属当前用户） | 是 |
| GET | `/items/{item_id}` | 查询单个商品 | 否 |
| PUT | `/items/{item_id}` | 更新商品（仅限本人） | 是 |
| DELETE | `/items/{item_id}` | 删除商品（仅限本人） | 是 |
| GET | `/json` | 返回 JSON | 否 |
| GET | `/html` | 返回 HTML | 否 |
| GET | `/file` | 返回文件 | 否 |
| GET | `/redirect` | 重定向到首页 | 否 |
| POST | `/send` | 后台任务发送通知 | 否 |
| POST | `/upload` | 文件上传 | 否 |
| GET | `/static/hello.html` | 静态文件 | 否 |

## 首页与基础接口

### GET /
返回 Hello World。

响应示例：
```json
{"message": "Hello World"}
```

### GET /hello/{name}
路径参数 `name`：字符串。

请求示例：
```text
GET /hello/User
```

响应示例：
```json
{"message": "Hello User"}
```

## 认证接口

### POST /auth/login
登录成功返回 JWT。

请求格式：`application/x-www-form-urlencoded`

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| username | string | 是 | 用户名 |
| password | string | 是 | 密码 |

请求示例：
```text
POST /auth/login
Content-Type: application/x-www-form-urlencoded

username=authuser&password=abc123
```

响应示例：
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

状态码：
- 200：登录成功
- 401：用户名或密码错误

## 用户接口

### POST /users/register
注册新用户，密码自动 bcrypt 哈希后入库。

请求体 `UserRegister`：

| 字段 | 类型 | 必填 | 校验 |
|------|------|------|------|
| username | string | 是 | 3-20 个字符 |
| password | string | 是 | 6-72 个字符 |
| age | integer | 否 | 默认 18，0-150 |
| email | string/null | 否 | 邮箱格式 |

请求示例：
```json
{
  "username": "authuser",
  "password": "abc123",
  "age": 20,
  "email": "authuser@example.com"
}
```

响应示例（201）：
```json
{
  "id": 6,
  "username": "authuser",
  "age": 20,
  "email": "authuser@example.com",
  "created_at": "2026-08-08T16:30:34.789864"
}
```

状态码：
- 201：注册成功
- 400：用户名已存在或参数校验失败

### GET /users
分页返回所有用户，不包含 password。

查询参数：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| page | integer | 1 | 页码，从 1 开始 |
| size | integer | 10 | 每页数量，最大 100 |

响应示例（200）：
```json
[
  {
    "id": 1,
    "username": "testuser",
    "age": 20,
    "email": "test@example.com",
    "created_at": "2026-08-02T14:12:53.570176"
  }
]
```

### GET /users/me
需要认证头 `Authorization: Bearer <access_token>`。

响应示例（200）：
```json
{
  "id": 6,
  "username": "authuser",
  "age": 20,
  "email": "authuser@example.com",
  "created_at": "2026-08-08T16:30:34.789864"
}
```

状态码：
- 200：成功
- 401：未携带 token、token 无效或用户不存在

### GET /users/{user_id}
路径参数 `user_id`：整数，用户主键。

响应示例（200）：
```json
{
  "id": 6,
  "username": "authuser",
  "age": 20,
  "email": "authuser@example.com",
  "created_at": "2026-08-08T16:30:34.789864"
}
```

状态码：
- 200：成功
- 404：用户不存在
- 422：user_id 不是整数

## 商品接口

### GET /news
查询参数示例。

| 参数 | 类型 | 默认值 | 校验 |
|------|------|--------|------|
| skip | integer | 0 | 0 <= skip < 100 |
| limit | integer | 10 | 1 <= limit <= 100 |

响应示例：
```json
{"skip": 0, "limit": 10}
```

### GET /items
商品分页列表。

查询参数：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| page | integer | 1 | 页码，从 1 开始 |
| size | integer | 10 | 每页数量，最大 100 |

响应示例（200）：
```json
[
  {
    "id": 1,
    "name": "Python Book",
    "price": 59.9,
    "user_id": 3,
    "created_at": "2026-08-02T14:16:52.522422"
  }
]
```

### POST /items
创建商品，需要登录，商品自动归属当前登录用户。

请求头：
```text
Authorization: Bearer <access_token>
```

请求体 `ItemCreate`：

| 字段 | 类型 | 必填 | 校验 |
|------|------|------|------|
| name | string | 是 | 1-50 个字符 |
| price | number | 是 | >= 0 |

请求示例：
```json
{
  "name": "Python Book",
  "price": 59.9
}
```

状态码：
- 201：创建成功
- 401：未登录或 token 无效
- 422：参数校验失败

### GET /items/{item_id}
按主键查询商品。

状态码：
- 200：成功
- 404：商品不存在

### PUT /items/{item_id}
部分更新商品，只更新请求体里传入的字段；只能更新自己创建的商品。

请求头：
```text
Authorization: Bearer <access_token>
```

请求体 `ItemUpdate`：

| 字段 | 类型 | 必填 | 校验 |
|------|------|------|------|
| name | string/null | 否 | 1-50 个字符 |
| price | number/null | 否 | >= 0 |

请求示例：
```json
{"price": 79.9}
```

状态码：
- 200：更新成功
- 404：商品不存在
- 401：未登录或 token 无效
- 403：无权操作该商品

### DELETE /items/{item_id}
删除商品，只能删除自己创建的商品。

请求头：
```text
Authorization: Bearer <access_token>
```

状态码：
- 204：删除成功，无响应体
- 404：商品不存在
- 401：未登录或 token 无效
- 403：无权操作该商品

## 文件与响应接口

### GET /json
返回 JSONResponse 示例：
```json
{"msg": "这是JSON"}
```

### GET /html
返回 HTMLResponse 示例：
```html
<h1>Hello FastAPI</h1>
```

### GET /file
返回 `static/hello.html` 文件。

### GET /redirect
重定向到 `/`。

### POST /send
后台任务发送通知，立即返回受理结果。

请求格式：`application/x-www-form-urlencoded`

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| email | string | 是 | 收件邮箱 |

响应示例：
```json
{"message": "已受理"}
```

### POST /upload
文件上传。

请求格式：`multipart/form-data`

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| username | string | 是 | 用户名 |
| file | file | 是 | 上传文件 |

响应示例：
```json
{
  "username": "zhangsan",
  "filename": "hello.txt",
  "size": 11
}
```

## 静态文件

### GET /static/hello.html
返回 `static` 目录下的静态文件。
