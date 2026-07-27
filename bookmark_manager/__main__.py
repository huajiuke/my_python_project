"""书签管理器 - CLI 入口"""

from bookmark_manager.database import (
    get_session, create_user, list_users, get_user_by_name,
    add_bookmark, list_bookmarks, delete_bookmark,
)


def print_help():
    print("""用法:
  user <用户名>                                  创建用户 / 切换用户
  users                                          列出所有用户
  add <标题> <URL> [-d <描述>]                    添加书签
  list [--all]                                   列出书签
  del <id>                                       删除书签
  whoami                                         当前用户
  help                                           帮助
  exit                                           退出
""")


def main():
    current_user_id = None

    print("书签管理器 v1.0  （输入 help 查看命令，exit 退出）")

    while True:
        try:
            raw = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not raw:
            continue

        parts = raw.split()
        cmd = parts[0].lower()

        if cmd == "exit":
            break

        elif cmd == "help":
            print_help()

        elif cmd == "users":
            with get_session() as session:
                list_users(session)

        elif cmd == "user" and len(parts) >= 2:
            username = parts[1]
            with get_session() as session:
                user = get_user_by_name(session, username)
                if user:
                    current_user_id = user.id
                    print(f"  切换到用户: {user.username}")
                else:
                    user = create_user(session, username)
                    current_user_id = user.id

        elif cmd == "whoami":
            if current_user_id is None:
                print("  未选择用户，先用 user <用户名> 创建或切换")
            else:
                with get_session() as session:
                    user = session.get(User, current_user_id)
                    print(f"  当前用户: {user.username} (id={user.id})")

        elif cmd == "list":
            if current_user_id is None:
                print("  请先用 user <用户名> 选择用户")
                continue
            with get_session() as session:
                list_bookmarks(session, current_user_id)

        elif cmd == "add" and len(parts) >= 3:
            if current_user_id is None:
                print("  请先用 user <用户名> 选择用户")
                continue
            title = parts[1]
            url = parts[2]
            desc = ""
            for i, p in enumerate(parts[3:], start=3):
                if p == "-d" and i + 1 < len(parts):
                    desc = parts[i + 1]
            with get_session() as session:
                add_bookmark(session, current_user_id, title, url, desc)

        elif cmd == "del" and len(parts) >= 2:
            try:
                bm_id = int(parts[1])
            except ValueError:
                print("  id 必须是数字")
                continue
            with get_session() as session:
                delete_bookmark(session, bm_id)

        else:
            print("  未知命令，输入 help 查看用法")


if __name__ == "__main__":
    # 循环引用：只在运行时导入 User 用于 whoami 的类型提示
    from bookmark_manager.models import User
    main()
