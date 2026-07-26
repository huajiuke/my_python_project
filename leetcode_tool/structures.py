"""LeetCode 常用数据结构：ListNode、TreeNode 及数组互转"""

from typing import List, Optional


# ── ListNode ─────────────────────────────────────────────

class ListNode:
    """单链表节点"""

    def __init__(self, val: int = 0, next_node: Optional["ListNode"] = None):
        self.val = val
        self.next = next_node

    def __repr__(self):
        return f"ListNode({self.val})"


def create_list_node(arr: List[int]) -> Optional[ListNode]:
    """从数组构建链表（LeetCode 输入格式）"""
    if not arr:
        return None
    head = ListNode(arr[0])
    curr = head
    for val in arr[1:]:
        curr.next = ListNode(val)
        curr = curr.next
    return head


def list_node_to_list(head: Optional[ListNode]) -> List[int]:
    """将链表转回数组"""
    result = []
    curr = head
    while curr:
        result.append(curr.val)
        curr = curr.next
    return result


# ── TreeNode ─────────────────────────────────────────────

class TreeNode:
    """二叉树节点"""

    def __init__(self, val: int = 0, left: Optional["TreeNode"] = None,
                 right: Optional["TreeNode"] = None):
        self.val = val
        self.left = left
        self.right = right

    def __repr__(self):
        return f"TreeNode({self.val})"


def create_tree_node(arr: List[Optional[int]]) -> Optional[TreeNode]:
    """从层序遍历数组构建二叉树（LeetCode 输入格式）
    None 表示空节点。例如 [3,9,20,None,None,15,7]
    """
    if not arr or arr[0] is None:
        return None

    root = TreeNode(arr[0])
    queue = [root]
    i = 1

    while queue and i < len(arr):
        node = queue.pop(0)

        if i < len(arr) and arr[i] is not None:
            node.left = TreeNode(arr[i])
            queue.append(node.left)
        i += 1

        if i < len(arr) and arr[i] is not None:
            node.right = TreeNode(arr[i])
            queue.append(node.right)
        i += 1

    return root


def tree_node_to_list(root: Optional[TreeNode]) -> List[Optional[int]]:
    """将二叉树转回层序遍历列表（LeetCode 输出格式）"""
    if not root:
        return []

    result = []
    queue = [root]

    while queue:
        node = queue.pop(0)
        if node:
            result.append(node.val)
            queue.append(node.left)
            queue.append(node.right)
        else:
            result.append(None)

    # 去掉尾部连续的 None（LeetCode 也是这么做的）
    while result and result[-1] is None:
        result.pop()

    return result
