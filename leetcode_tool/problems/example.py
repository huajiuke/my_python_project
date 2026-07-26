"""示例题目：两数之和、二叉树中序遍历、反转链表

用法:
    cd D:/13155/PythonLearn
    python -m leetcode_tool.problems.example
"""
from typing import List, Optional

from leetcode_tool.runner import run_test
from leetcode_tool.structures import ListNode, TreeNode
from leetcode_tool import (
    create_list_node, list_node_to_list,
    create_tree_node, tree_node_to_list,
)


# ── 题目 1：两数之和 ────────────────────────────
# LeetCode 1. Two Sum

class Solution:
    def twoSum(self, nums: List[int], target: int) -> List[int]:
        seen = {}
        for i, num in enumerate(nums):
            complement = target - num
            if complement in seen:
                return [seen[complement], i]
            seen[num] = i
        return []


# ── 题目 2：二叉树中序遍历 ──────────────────────
# LeetCode 94. Binary Tree Inorder Traversal

class Solution2:
    def inorderTraversal(self, root: Optional[TreeNode]) -> List[int]:
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

class Solution3:
    def reverseList(self, head: Optional[ListNode]) -> Optional[ListNode]:
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
    print()
    print("题目 1: 两数之和")
    print("-" * 40)
    run_test(Solution().twoSum, [
        (([2, 7, 11, 15], 9), [0, 1]),
        (([3, 2, 4], 6), [1, 2]),
        (([3, 3], 6), [0, 1]),
        (([1, 2, 3, 4], 8), []),
    ])

    print()
    print("题目 2: 二叉树中序遍历")
    print("-" * 40)
    run_test(
        Solution2().inorderTraversal,
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
        Solution3().reverseList,
        [
            (([1, 2, 3, 4, 5],), [5, 4, 3, 2, 1]),
            (([1, 2],), [2, 1]),
            (([],), []),
        ],
        input_transform=create_list_node,
        output_transform=list_node_to_list,
    )
