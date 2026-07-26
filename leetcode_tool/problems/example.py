"""示例题目：两数之和、二叉树中序遍历、反转链表

用法:
    cd D:/13155/PythonLearn
    python -m leetcode_tool.problems.example
"""

from leetcode_tool.runner import run_test
from leetcode_tool.structures import (
    create_list_node, list_node_to_list,
    create_tree_node, tree_node_to_list,
)
from typing import List, Optional


# ── 题目 1：两数之和 ────────────────────────────
# LeetCode 1. Two Sum

def two_sum(nums: List[int], target: int) -> List[int]:
    """给定一个整数数组和目标值，返回两数之和等于目标值的下标"""
    seen = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            return [seen[complement], i]
        seen[num] = i
    return []


# ── 题目 2：二叉树中序遍历 ──────────────────────
# LeetCode 94. Binary Tree Inorder Traversal

def inorder_traversal(root: Optional[TreeNode]) -> List[int]:
    """二叉树中序遍历（递归版）"""
    res = []

    def dfs(node):
        if node is None:
            return
        dfs(node.left)
        res.append(node.val)
        dfs(node.right)

    dfs(root)
    return res


# ── 题目 3：反转链表 ────────────────────────────
# LeetCode 206. Reverse Linked List

def reverse_list(head: Optional[ListNode]) -> Optional[ListNode]:
    """反转单链表"""
    prev = None
    curr = head
    while curr:
        next_node = curr.next
        curr.next = prev
        prev = curr
        curr = next_node
    return prev


# ── 运行测试 ────────────────────────────────────

if __name__ == "__main__":
    from leetcode_tool.structures import TreeNode, ListNode

    print()
    print("题目 1: 两数之和")
    print("-" * 40)
    run_test(two_sum, [
        (([2, 7, 11, 15], 9), [0, 1]),
        (([3, 2, 4], 6), [1, 2]),
        (([3, 3], 6), [0, 1]),
        (([1, 2, 3, 4], 8), []),
    ])

    print()
    print("题目 2: 二叉树中序遍历")
    print("-" * 40)
    run_test(
        inorder_traversal,
        [
            (([1, None, 2, 3],), [1, 3, 2]),
            (([],), []),
            (([1],), [1]),
        ],
        input_transform=create_tree_node,
    )

    print()
    print("题目 3: 反转链表")
    print("-" * 40)
    run_test(
        reverse_list,
        [
            (([1, 2, 3, 4, 5],), [5, 4, 3, 2, 1]),
            (([1, 2],), [2, 1]),
            (([],), []),
        ],
        input_transform=create_list_node,
        output_transform=list_node_to_list,
    )
